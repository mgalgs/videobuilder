"""A page screenshot as a person sees it once the page has settled: Chromium
driven over the DevTools protocol on a pipe (fds 3 and 4, never a TCP port),
so the gatherer can wait for the page to load and go quiet, let web fonts
arrive, finish its animations, scroll it so scroll-triggered reveals fire,
and hide a cookie/consent notice -- hidden, never accepted -- before the
shot. Standard library only: a CDP message is JSON ended by a NUL byte.

Every bound is the caller's `timeout`: a page that never settles is shot at
the deadline rather than failing, and Chromium (with every process it
started) is killed on the way out whatever happens.
"""
import base64
import json
import os
import select
import signal
import tempfile
import time
from pathlib import Path

# Kept back from the deadline for the capture itself.
CAPTURE_RESERVE = 2.0
QUIET = 0.5
# How long settling waits for the load event, then for the network to go
# quiet: one subresource that never ends (a stalled pixel, a long-poll, an
# event stream) must not use up the page's whole budget before the cleanup.
LOAD_WAIT = 8.0
QUIET_WAIT = 3.0
SCROLL_STEPS = 40

# Finishes animations instantly. 0.01ms rather than 0, so transitionend and
# animationend still fire for scripts that wait on them.
_STILL_CSS = ('*,*::before,*::after{animation-duration:0.01ms!important;animation-delay:0s!important;'
              'transition-duration:0.01ms!important;transition-delay:0s!important;'
              'scroll-behavior:auto!important}')

_SETTLE_JS = '''(async (css, steps) => {
  const frame = () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  const style = document.createElement('style');
  style.textContent = css;
  (document.head || document.documentElement).appendChild(style);
  const step = Math.max(200, innerHeight * 0.8);
  for (let i = 0, y = 0; i < steps && y < document.documentElement.scrollHeight; i++, y += step) {
    scrollTo(0, y);
    await frame();
  }
  scrollTo(0, 0);
  await frame();
})'''

# Hides (never accepts) a cookie/consent notice: a fixed or sticky element
# whose id, class, aria-label or text says cookie/consent/GDPR, plus the
# full-screen backdrop such a notice dims the page with, and undoes the
# scroll lock it set. A fixed wrapper holding the page itself is left alone.
_CONSENT_JS = r'''(() => {
  const named = /cookie|consent|gdpr|ccpa|privacy|datenschutz|einwilligung|consentement|consentimiento|consenso|rgpd|dsgvo/i;
  const said = /cookie|consent|gdpr|ccpa|datenschutz|einwilligung|consentement|consentimiento|consenso|rgpd|dsgvo/i;
  const hide = el => el.style.setProperty('display', 'none', 'important');
  const pinned = el => /^(fixed|sticky)$/.test(getComputedStyle(el).position);
  const holdsPage = el => el.querySelector('main, article, h1') || (el.innerText || '').length > 3000;
  const all = Array.from(document.body ? document.body.querySelectorAll('*') : []).slice(0, 8000);
  let hidden = 0;
  for (const el of all) {
    if (!el.isConnected || el.closest('[data-vb-hidden]') || !pinned(el) || holdsPage(el)) continue;
    const label = [el.id, typeof el.className === 'string' ? el.className : '', el.getAttribute('aria-label') || ''].join(' ');
    if (named.test(label) || said.test(el.innerText || '')) {
      el.setAttribute('data-vb-hidden', '');
      hide(el);
      hidden++;
    }
  }
  if (!hidden) return 0;
  for (const el of all) {
    if (el.hasAttribute('data-vb-hidden') || getComputedStyle(el).position !== 'fixed') continue;
    const box = el.getBoundingClientRect();
    if (box.width >= innerWidth * 0.9 && box.height >= innerHeight * 0.9 && !(el.innerText || '').trim()) hide(el);
  }
  for (const el of [document.documentElement, document.body]) {
    if (getComputedStyle(el).overflowY === 'hidden') el.style.setProperty('overflow', 'visible', 'important');
  }
  return hidden;
})()'''


class Closed(Exception):
    """Chromium closed the pipe (it exited or crashed)."""


class _Pipe:
    """The DevTools protocol over Chromium's --remote-debugging-pipe."""

    def __init__(self, write_fd, read_fd):
        self.write_fd, self.read_fd = write_fd, read_fd
        self.buffer = b''
        self.next_id = 0
        self.events = []

    def send(self, method, params=None, session=None):
        self.next_id += 1
        message = {'id': self.next_id, 'method': method, 'params': params or {}}
        if session:
            message['sessionId'] = session
        data = json.dumps(message).encode() + b'\0'
        while data:
            data = data[os.write(self.write_fd, data):]
        return self.next_id

    def _read(self, deadline):
        """The next message, or None at the deadline."""
        while b'\0' not in self.buffer:
            left = deadline - time.monotonic()
            if left <= 0 or not select.select([self.read_fd], [], [], left)[0]:
                return None
            chunk = os.read(self.read_fd, 1 << 16)
            if not chunk:
                raise Closed('chromium closed the pipe')
            self.buffer += chunk
        raw, self.buffer = self.buffer.split(b'\0', 1)
        return json.loads(raw)

    def call(self, method, params=None, session=None, deadline=None):
        """The result of one command; TimeoutError at the deadline. Events
        that arrive meanwhile are kept for `wait_event`."""
        wanted = self.send(method, params, session)
        while True:
            message = self._read(deadline)
            if message is None:
                raise TimeoutError(f'{method}: no answer in time')
            if message.get('id') == wanted:
                if 'error' in message:
                    raise RuntimeError(f"{method}: {message['error'].get('message')}")
                return message.get('result', {})
            if 'method' in message:
                self.events.append(message)

    def wait_event(self, method, deadline):
        """True once `method` has arrived, False at the deadline."""
        while True:
            if any(event['method'] == method for event in self.events):
                return True
            message = self._read(deadline)
            if message is None:
                return False
            if 'method' in message:
                self.events.append(message)

    def wait_quiet(self, deadline, quiet=QUIET):
        """Wait until no request has been in flight for `quiet` seconds, or
        the deadline."""
        pending = set()
        since = time.monotonic()
        while time.monotonic() < deadline:
            for event in self.events:
                method, request = event['method'], event.get('params', {}).get('requestId')
                if method == 'Network.requestWillBeSent':
                    pending.add(request)
                    since = time.monotonic()
                elif method in ('Network.loadingFinished', 'Network.loadingFailed'):
                    pending.discard(request)
                    since = time.monotonic()
            self.events.clear()
            if not pending and time.monotonic() - since >= quiet:
                return True
            message = self._read(min(deadline, time.monotonic() + quiet / 5))
            if message is not None and 'method' in message:
                self.events.append(message)
        return False


def command(chromium, size, profile, proxy_args, extra_args=()):
    """Chromium's command line: headless, its own sandbox, every request
    through the guard (`proxy_args`), DevTools on the pipe only."""
    return [chromium, '--headless=new', '--disable-gpu', '--disable-dev-shm-usage', '--hide-scrollbars',
            '--no-first-run', '--force-prefers-reduced-motion', '--remote-debugging-pipe',
            f'--user-data-dir={profile}', *proxy_args, f'--window-size={size[0]},{size[1]}',
            *extra_args, 'about:blank']


def _spawn(argv):
    """Start Chromium in its own process group with the DevTools pipe on fds
    3 (commands in) and 4 (replies out); returns (pid, pipe)."""
    to_chromium, our_write = os.pipe()
    our_read, from_chromium = os.pipe()
    null = os.open(os.devnull, os.O_RDWR)
    try:
        # posix_spawn rather than subprocess: it can put the pipe ends on
        # exactly fds 3 and 4 without a preexec_fn (unsafe with threads).
        pid = os.posix_spawn(argv[0], argv, os.environ, setsid=True, file_actions=[
            (os.POSIX_SPAWN_DUP2, null, 0), (os.POSIX_SPAWN_DUP2, null, 1), (os.POSIX_SPAWN_DUP2, null, 2),
            (os.POSIX_SPAWN_DUP2, to_chromium, 3), (os.POSIX_SPAWN_DUP2, from_chromium, 4)])
    except BaseException:
        os.close(our_write)
        os.close(our_read)
        raise
    finally:
        for fd in (to_chromium, from_chromium, null):
            os.close(fd)
    return pid, _Pipe(our_write, our_read)


def _kill(pid):
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    os.waitpid(pid, 0)


def screenshot(chromium, url, size, timeout, proxy_args, extra_args=()):
    """A PNG of `url` at viewport `size` (width, height), within `timeout`
    seconds. `extra_args` is for tests only (e.g. --no-sandbox where the
    test machine has no user namespaces); production passes none."""
    deadline = time.monotonic() + timeout
    settle_by = deadline - min(CAPTURE_RESERVE, timeout * 0.25)
    # A throwaway profile per visit: no cookies or storage carry between pages or gathers.
    with tempfile.TemporaryDirectory(prefix='vb-gather-', ignore_cleanup_errors=True) as profile:
        pid, pipe = _spawn(command(chromium, size, Path(profile) / 'profile', proxy_args, extra_args))
        try:
            target = pipe.call('Target.createTarget', {'url': 'about:blank'}, deadline=settle_by)['targetId']
            session = pipe.call('Target.attachToTarget', {'targetId': target, 'flatten': True},
                                deadline=settle_by)['sessionId']
            for method, params in (('Page.enable', {}), ('Network.enable', {}),
                                   ('Emulation.setDeviceMetricsOverride',
                                    {'width': size[0], 'height': size[1], 'deviceScaleFactor': 1,
                                     'mobile': False})):
                pipe.call(method, params, session, deadline=settle_by)
            try:
                _settle(pipe, session, url, settle_by)
            except TimeoutError:
                pass  # shot as it stands at the deadline
            pipe.events.clear()
            shot = pipe.call('Page.captureScreenshot', {'format': 'png'}, session, deadline=deadline)
        finally:
            os.close(pipe.write_fd)
            os.close(pipe.read_fd)
            _kill(pid)
    data = base64.b64decode(shot['data'])
    if not data:
        raise ValueError('chromium produced no screenshot')
    return data


def _settle(pipe, session, url, deadline):
    """Load `url` and bring it to rest; TimeoutError if the deadline comes first."""
    def evaluate(expression, until=None):
        return pipe.call('Runtime.evaluate', {'expression': expression, 'awaitPromise': True},
                         session, deadline=until or deadline)

    pipe.call('Page.navigate', {'url': url}, session, deadline=deadline)
    # No load event in time still settles the page as it stands.
    pipe.wait_event('Page.loadEventFired', min(deadline, time.monotonic() + LOAD_WAIT))
    pipe.wait_quiet(min(deadline, time.monotonic() + QUIET_WAIT))
    # Fonts get a bounded wait of their own: a font that never arrives must
    # not cost the rest of the settling.
    try:
        evaluate('document.fonts.ready.then(() => true)', min(deadline, time.monotonic() + 3))
    except TimeoutError:
        pass
    evaluate(_CONSENT_JS)
    evaluate(f'{_SETTLE_JS}({json.dumps(_STILL_CSS)}, {SCROLL_STEPS})')
    # Scrolling can load lazy images and start late banners or animations.
    pipe.wait_quiet(min(deadline, time.monotonic() + QUIET_WAIT))
    evaluate('document.getAnimations().forEach(a => { try { a.finish() } catch (e) {} })')
    evaluate(_CONSENT_JS)
    evaluate('new Promise(r => setTimeout(r, 300))')
