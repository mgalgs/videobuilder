"""Gathering: visiting the links given when starting a video from scratch, so
the builder never has to -- the builder's sandbox stays offline. The editor
crawls same-site pages breadth-first from the given links, through
`guard.GuardProxy`, before the first note is queued, and keeps per page: the
final URL, the title, readable text, and a desktop and a phone screenshot.
`write_attachments` turns that into ordinary note attachments plus one index
attachment listing every page.
"""
import html.parser
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import urljoin, urlsplit
import urllib.error
import urllib.request

from . import guard

MAX_PAGES = 10
TIME_BUDGET = 120
PAGE_TIMEOUT = 20
MAX_TEXT = 20_000
DESKTOP = (1440, 900)
PHONE = (390, 844)
USER_AGENT = 'Mozilla/5.0 (compatible; videobuilder-gatherer/1.0)'
_SKIP = re.compile(r'(?:^|[/._-])(log[-_]?(?:in|on|out|off)|sign[-_]?(?:in|up|out))(?:$|[/._?#-])', re.I)
_BOILERPLATE = ('script', 'style', 'nav', 'header', 'footer')


class _PageParser(html.parser.HTMLParser):
    """Rendered-free: the `<title>`, visible text with script/style/nav/
    header/footer stripped, and every `<a href>`, from raw HTML."""

    def __init__(self):
        super().__init__()
        self.links = []
        self._skip_depth = 0
        self._in_title = False
        self._title = []
        self._text = []

    def handle_starttag(self, tag, attrs):
        if tag in _BOILERPLATE:
            self._skip_depth += 1
        elif tag == 'title':
            self._in_title = True
        elif tag == 'a':
            href = dict(attrs).get('href')
            if href:
                self.links.append(href)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag in _BOILERPLATE:
            self._skip_depth -= 1
        elif tag == 'title':
            self._in_title = False

    def handle_endtag(self, tag):
        if tag in _BOILERPLATE and self._skip_depth:
            self._skip_depth -= 1
        elif tag == 'title':
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self._title.append(data)
        elif not self._skip_depth:
            stripped = ' '.join(data.split())
            if stripped:
                self._text.append(stripped)

    @property
    def title(self):
        return ' '.join(''.join(self._title).split())

    @property
    def text(self):
        return '\n'.join(self._text)


def find_chromium():
    for name in ('chromium', 'chromium-browser', 'google-chrome'):
        path = shutil.which(name)
        if path:
            return path
    return '/usr/bin/chromium' if Path('/usr/bin/chromium').is_file() else None


def _registrable(host):
    host = (host or '').lower().rstrip('.')
    return host[4:] if host.startswith('www.') else host


def _same_site(url, site_hosts):
    host = _registrable(urlsplit(url).hostname)
    return bool(host) and host in site_hosts


def _looks_skippable(url):
    return bool(_SKIP.search(urlsplit(url).path))


def _fetch(opener, url, timeout, allow_loopback):
    parts = urlsplit(url)
    port = parts.port or (443 if parts.scheme == 'https' else 80)
    # A fast, explicit refusal for the link itself; the proxy behind `opener`
    # re-checks regardless, including every redirect this fetch follows.
    guard.resolve_and_check(parts.hostname, port, allow_loopback=allow_loopback)
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'text/html'})
    with opener.open(request, timeout=timeout) as response:
        final_url = response.geturl()
        ctype = response.headers.get_content_type()
        if ctype != 'text/html':
            raise ValueError(f'not an HTML page ({ctype})')
        data = response.read(MAX_TEXT * 8 + 1)
    return final_url, data.decode('utf-8', 'replace')


def _screenshot(chromium, proxy_port, url, size, timeout):
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as handle:
        path = Path(handle.name)
    try:
        subprocess.run([chromium, '--headless=new', '--disable-gpu', '--disable-dev-shm-usage',
                        '--hide-scrollbars', '--no-first-run', '--virtual-time-budget=8000',
                        *guard.chromium_proxy_args(proxy_port),
                        f'--screenshot={path}', f'--window-size={size[0]},{size[1]}', url],
                       capture_output=True, timeout=timeout, check=True)
        data = path.read_bytes()
    finally:
        path.unlink(missing_ok=True)
    if not data:
        raise ValueError('chromium produced no screenshot')
    return data


_AUTO = object()


def crawl(links, max_pages=MAX_PAGES, time_budget=TIME_BUDGET, page_timeout=PAGE_TIMEOUT,
         allow_loopback=False, chromium=_AUTO):
    """Visit `links` and, breadth-first, same-site pages reachable from them,
    up to `max_pages` pages in total within `time_budget` seconds. Returns
    (pages, errors): `pages` is a list of dicts (url, title, text,
    desktop_png, phone_png -- the last two None without a browser), and
    `errors` a list of (url, reason) for every link skipped or that failed,
    in the order encountered. Raises only for a bad call (no links)."""
    if not links:
        raise ValueError('no links to gather')
    chromium = find_chromium() if chromium is _AUTO else chromium
    site_hosts = {_registrable(urlsplit(link).hostname) for link in links}
    proxy = guard.GuardProxy(allow_loopback=allow_loopback)
    pages, errors, seen = [], [], set()
    queue = list(dict.fromkeys(url.split('#', 1)[0] for url in links))
    deadline = time.monotonic() + time_budget
    fetcher = guard.opener(proxy.port)
    try:
        while queue and len(pages) < max_pages and time.monotonic() < deadline:
            url = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            if _looks_skippable(url):
                errors.append((url, 'looks like a sign-in or sign-out page'))
                continue
            remaining = max(1, min(page_timeout, deadline - time.monotonic()))
            try:
                final_url, body = _fetch(fetcher, url, remaining, allow_loopback)
            except guard.Refused as exc:
                errors.append((url, 'blocked address'))
                continue
            except Exception as exc:
                errors.append((url, f'fetch failed: {exc}'))
                continue
            parser = _PageParser()
            try:
                parser.feed(body)
            except Exception:
                pass
            desktop = phone = None
            if chromium:
                try:
                    remaining = max(1, min(page_timeout, deadline - time.monotonic()))
                    desktop = _screenshot(chromium, proxy.port, final_url, DESKTOP, remaining)
                    remaining = max(1, min(page_timeout, deadline - time.monotonic()))
                    phone = _screenshot(chromium, proxy.port, final_url, PHONE, remaining)
                except Exception as exc:
                    errors.append((url, f'screenshot failed: {exc}'))
            else:
                errors.append((url, 'links not gathered: no browser'))
            pages.append(dict(url=final_url, title=parser.title, text=parser.text[:MAX_TEXT],
                              desktop_png=desktop, phone_png=phone))
            for href in parser.links:
                absolute = urljoin(final_url, href).split('#', 1)[0]
                scheme = urlsplit(absolute).scheme
                if scheme in ('http', 'https') and absolute not in seen and _same_site(absolute, site_hosts):
                    queue.append(absolute)
    finally:
        # Refusals the proxy itself caught (a redirect or a Chromium subresource the
        # per-link pre-check above never saw) are reported too, not just top-level skips.
        errors.extend(proxy.log)
        proxy.close()
    return pages, errors


def write_attachments(store, video, pages, errors, reserved_files=0, reserved_bytes=0):
    """Upload each page's text and screenshots as ordinary note attachments
    plus one index attachment listing every page, and return the attachment
    ids (index first). A single oversized file (bigger than the store's own
    per-file limit -- not expected at these screenshot sizes) has that limit
    raised just for this upload, noted in the index: the one case the brief
    allows raising a limit for.

    `reserved_files`/`reserved_bytes` are the count and size of attachments
    the note already carries (e.g. the director's own uploads), so the
    store's overall `max_files`/`max_message` budget -- shared with every
    other note -- is honored for the combined set, not just the pages
    gathered here. Once that budget (minus one slot reserved for the index
    itself) is spent, remaining page attachments are skipped and noted
    rather than silently exceeding it."""
    max_files = getattr(store, 'max_files', None)
    max_message = getattr(store, 'max_message', None)
    budget_files = None if max_files is None else max(0, max_files - reserved_files - 1)
    budget_bytes = None if max_message is None else max(0, max_message - reserved_bytes)
    ids = []
    lines = ['# Gathered pages', '']
    spent_files = spent_bytes = 0
    limit_hit = False
    for n, page in enumerate(pages, 1):
        lines.append(f"{n}. {page['title'] or '(untitled)'} -- {page['url']}")
        for label, name, ctype, data in (
                ('text', f'page-{n}.txt', 'text/plain', page['text'].encode('utf-8')),
                ('desktop screenshot', f'page-{n}-desktop.png', 'image/png', page['desktop_png']),
                ('phone screenshot', f'page-{n}-phone.png', 'image/png', page['phone_png'])):
            if not data:
                continue
            if ((budget_files is not None and spent_files >= budget_files) or
                    (budget_bytes is not None and spent_bytes + len(data) > budget_bytes)):
                lines.append(f'   {label}: skipped (attachment limit reached)')
                limit_hit = True
                continue
            max_file = getattr(store, 'max_file', None)
            oversize = max_file is not None and len(data) > max_file
            try:
                record = store.upload(video, name, ctype, data, allow_oversize=oversize)
            except ValueError as exc:
                lines.append(f'   {label}: skipped ({exc})')
                continue
            spent_files += 1
            spent_bytes += record['size']
            suffix = ' (file size limit raised to fit)' if oversize else ''
            ids.append(record['id'])
            lines.append(f"   {label}: {record['name']}{suffix}")
    for url, reason in errors:
        lines.append(f'- skipped {url}: {reason}')
    if limit_hit:
        lines.append('')
        lines.append('Some gathered attachments were skipped: the note attachment limit was reached.')
    index = store.upload(video, 'gathered-pages.md', 'text/plain', '\n'.join(lines).encode('utf-8'))
    return [index['id'], *ids]
