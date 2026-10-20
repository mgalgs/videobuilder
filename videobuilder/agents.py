"""Replaceable agent runners (stdlib only).

CommandBackend invokes ``submit_command + [request.json]`` and
``poll_command + [handle]`` without a shell. The request contains the note
fields plus project, film, image, note_file, state_dir, session and draft.
submit stdout is JSON {"handle": "opaque string"}; poll stdout is JSON
{"state": "queued|working|replied|failed", "reply": "text or null",
"branch": "local branch or null", "cost_usd": number or null (optional),
"tokens": object or null (optional)}. cost_usd and tokens are whatever the
run cost and used, passed straight through to the note; a command that
never reports them simply omits the keys, and they stay null -- never
estimated, never zero. Commands must be idempotent for a note
id: a crash between external submission and persisting its handle can retry.
The stable per-video state_dir is the runner's resumable session, and draft
is the current linear branch (null after Accept/Drop). Runners must honor it.

ForkSandboxBackend is deliberately isolated here: run --resume STATE
[--base DRAFT] [extra_args] PROJECT NOTE prints a run directory (--base only
when a draft exists; without it the run starts from main); status --json RUN prints
the status above, optionally reply_file (otherwise RUN/outbox/reply.md),
total_cost_usd (every leg; cost_usd, the first leg's, is the fallback) and
usage (token counts); a missing or malformed value is recorded as null.
executable, submit_args, poll_args, extra_args are configurable argv lists
(executable is a string). No shell expansion is performed.

When extra_args carries --k8s (the backend is running notes as cluster jobs
via `fork-sandbox run --k8s`), ForkSandboxBackend also gains `peek(handle,
file=None, after=0)`, calling the read-only `<executable> k8s peek <handle>
--after AFTER [--file FILE]`: stdout is raw transcript bytes, and the last
stderr line, `peek: file=<name> next=<offset>`, is parsed into the (bytes,
name, offset) triple `transcript.read_feed` polls with (see its module
docstring). A silent, empty exit 0 (pod or transcript not there yet) is not
an error: it's reported back as no new bytes at the same file/offset. A
non-cluster backend (no --k8s) never gets a `peek` attribute at all, so
`hasattr(backend, 'peek')` is how a caller tells the two apart.

ForkSandboxBackend also has `compendium_source(note)`, the pinned videobuilder's
compendium directory if it has one, or None if context_root isn't configured or
the pin predates the compendium -- NoteStore._submit calls it (via `getattr`,
the same optional-attribute pattern as `peek`) to decide whether the builder's
prompt gets the "Start from the compendium" section. Other backends simply
don't have the attribute, which reads as "can't tell" there too.

On Kubernetes, a poll's raw state can also be "orphaned": the driver process
that was going to wait for the pod and collect its branch is dead, but the
pod itself is still alive. ForkSandboxBackend reacts by starting
`<executable> adopt <run-dir>` in the background -- at most once per run-dir
per backend instance, ever, even once that process has exited (an adopt
that refuses right away, e.g. because another adopt is already driving the
run, is not retried just because the pod is still reporting "orphaned") --
and reports the note as plain "working"
rather than exposing "orphaned" any further; the adopt process is reaped
(never left a zombie) on a later poll, and its stderr is logged on a nonzero
exit. Nothing else is done with the result: the following poll's raw state,
once adopt has either collected the run or given up, decides the note's fate
as usual. A "failed" state that also carries a "reason" (the driver died
before the note ever got a normal chance to fail) is turned into a
plain-language reply instead of leaving the note with no error text at all.
"""
import fcntl
import json
import logging
import re
import tempfile
import subprocess
import time
from dataclasses import asdict
from pathlib import Path

from .gitutil import git
from .notes import AgentBackend, AgentStatus, NullBackend
from .workers import pin_for, pinned_version

_logger = logging.getLogger(__name__)


def run(argv):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    if result.returncode:
        reason = result.stderr.strip()[-2000:] or result.stdout.strip()[-2000:]
        raise ValueError(f'{argv[0]} exited {result.returncode}: {reason}')
    return result.stdout.strip()


class CommandBackend(AgentBackend):
    name = 'command'

    def __init__(self, submit_command, poll_command):
        for command in (submit_command, poll_command):
            if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
                raise ValueError('agent commands must be nonempty argv lists')
        self.submit_command, self.poll_command = submit_command, poll_command

    def submit(self, note):
        request = Path(note['state_dir']) / (note['id'] + '.request.json')
        request.write_text(json.dumps(note), encoding='utf-8')
        handle = json.loads(run(self.submit_command + [str(request)]))['handle']
        if not isinstance(handle, str) or not handle:
            raise ValueError('submit must return a nonempty string handle')
        return handle

    def poll(self, handle):
        return AgentStatus(**json.loads(run(self.poll_command + [handle])))


CONTEXT_STAGING_ROOT = Path("/var/tmp/claude-scratch/forks")


def source_pin(pin, fallback):
    version = pinned_version(pin)
    if version == "unknown":
        raise ValueError(f"{pin}: no versioned videobuilder pin")
    for line in pin.read_text().splitlines():
        match = re.match(r"^\s*videobuilder\s*@\s*git\+(.+)@([^@\s#]+)", line, re.I)
        if match:
            return version, match.group(1), match.group(2)
    if not fallback:
        raise ValueError("editor.agent.videobuilder_repo is required for a == pin")
    return version, fallback, "v" + version


_PEEK_TIMEOUT = 10
_PEEK_STATUS = re.compile(r'^peek:\s*file=(\S+)\s+next=(\d+)\s*$')


class ForkSandboxBackend(AgentBackend):
    name = 'fork-sandbox'

    def __init__(self, executable='fork-sandbox', submit_args=None, poll_args=None, extra_args=None,
                 context_root=None, context_mount=None, videobuilder_repo=None):
        self.executable = executable
        self.submit_args = ['run'] if submit_args is None else submit_args
        self.poll_args = ['status', '--json'] if poll_args is None else poll_args
        self.extra_args = extra_args or []
        self.context_root = Path(context_root).resolve() if context_root else None
        self.context_mount = context_mount
        self.videobuilder_repo = videobuilder_repo
        self._adopting = {}  # run-dir -> (Popen, stderr tempfile), while this process's adopt runs
        self._adopted = set()  # run-dirs this backend instance has ever started an adopt for
        if self.context_root and not self.context_root.is_relative_to(CONTEXT_STAGING_ROOT):
            raise ValueError(f"editor.agent.context_root must be under {CONTEXT_STAGING_ROOT}")
        if '--k8s' in self.extra_args:
            self.peek = self._peek

    def _stage(self, note):
        """Make sure note['project']'s pinned videobuilder version is cloned under
        context_root, and return its directory (<context_root>/vNNN, holding a
        `videobuilder` checkout). Idempotent: a second call for an already-staged
        pin just checks the clone is there."""
        pin = pin_for(Path(note['project']) / note['film'], note['project'])
        if pin is None:
            raise ValueError('agent source staging needs a videobuilder requirements.txt pin')
        version, url, ref = source_pin(pin, self.videobuilder_repo)
        target = self.context_root / ('v' + version)
        self.context_root.mkdir(parents=True, exist_ok=True)
        with open(self.context_root / ('v' + version + '.lock'), 'a+b') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if not (target / 'videobuilder' / '.git').exists():
                with tempfile.TemporaryDirectory(prefix='v' + version + '-', dir=self.context_root) as temporary:
                    staged = Path(temporary) / 'videobuilder'
                    result = git(None, 'clone', '--depth', '1', '--branch', ref, url, str(staged),
                                hooks=False, check=False)
                    if result.returncode:
                        raise ValueError('could not stage pinned videobuilder: ' + result.stderr.strip())
                    Path(temporary).rename(target)
        return target

    def _context(self, note):
        target = self._stage(note)
        mount = self.context_mount or str(target)
        with open(note['note_file'], 'a', encoding='utf-8') as fh:
            fh.write(f"\nPinned videobuilder source: {mount}/videobuilder\n"
                     f"Use PYTHONPATH={mount}/videobuilder to render this video.\n"
                     f"Read {mount}/videobuilder/skill/make-a-video/SKILL.md.\n")
        return target

    def compendium_source(self, note):
        """Path to the staged pinned videobuilder's compendium package that this
        note will render with, or None when there's nothing staged to check
        (no context_root configured) or the pinned version predates the
        compendium -- either way, "can't tell" rather than an error (see
        NoteStore._submit, which calls this before the note's prompt is
        written). This calls _stage itself, the same real clone submit() does,
        so it costs nothing extra: submit() would stage the same pin anyway,
        and _stage is idempotent. One edge case: a transient clone failure
        here is swallowed into None, so the prompt omits the section even
        though submit()'s own _stage call can retry and succeed -- the prompt
        then describes a source that doesn't mention the compendium it was
        actually rendered with. Rare, and "can't tell" is an acceptable
        answer for it."""
        if not self.context_root:
            return None
        try:
            target = self._stage(note)
        except ValueError:
            return None
        compendium = target / 'videobuilder' / 'videobuilder' / 'compendium'
        return compendium if compendium.is_dir() else None

    def submit(self, note):
        context = self._context(note) if self.context_root else None
        base = ['--base', note['draft']] if note.get('draft') else []
        return run([self.executable, *self.submit_args, '--resume', note['state_dir'], *base,
                    *self.extra_args, *(['--context-ro', str(context)] if context else []),
                    *(['--attach-dir', note['attach_dir']] if note.get('attach_dir') else []),
                    note['project'], note['note_file']])

    def poll(self, handle):
        self._reap_adoptions()
        data = json.loads(run([self.executable, *self.poll_args, handle]))
        state = data['state']
        if state == 'orphaned':
            self._adopt(handle)
            state = 'working'
        reply = data.get('reply')
        if state == 'replied' and reply is None:
            path = Path(data.get('reply_file') or Path(handle) / 'outbox/reply.md')
            if path.is_file():
                reply = path.read_text(encoding='utf-8')
        if reply:
            reply = re.sub(r'^== result:[^\n]*==\n+', '', reply)
        if state == 'failed' and data.get('reason'):
            reply = ("The build was interrupted when the editor restarted, and its work "
                     "couldn't be recovered. Retry the note.")
        # total_cost_usd spans every leg of the run (review and fix legs too);
        # cost_usd is the first leg's alone. Token counts are under `usage`.
        cost = data.get('total_cost_usd', data.get('cost_usd'))
        if isinstance(cost, bool) or not isinstance(cost, (int, float)):
            cost = None
        tokens = data.get('usage', data.get('tokens'))
        return AgentStatus(state, reply, data.get('branch'), cost,
                           tokens if isinstance(tokens, dict) else None)

    def _adopt(self, handle):
        """Start `adopt <handle>` in the background, unless this backend instance
        has already started one for `handle` -- "at most once per run per
        editor process" (see the class docstring). That's tracked separately
        from `_adopting`, which only tells us whether one is still alive:
        once reaped, a finished (or refused) adopt must not be retried just
        because the pod is still reporting "orphaned"."""
        self._reap_adoptions()
        if handle in self._adopted:
            return
        self._adopted.add(handle)
        stderr = tempfile.TemporaryFile()
        process = subprocess.Popen([self.executable, 'adopt', handle], stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL, stderr=stderr)
        self._adopting[handle] = (process, stderr)

    def _reap_adoptions(self):
        """Collect any adopt process started by this backend instance that has
        since exited, so it never lingers as a zombie; a nonzero exit is logged
        and otherwise ignored, since the next ordinary poll decides the note's
        fate (see the class docstring)."""
        for handle, (process, stderr) in list(self._adopting.items()):
            if process.poll() is None:
                continue
            del self._adopting[handle]
            if process.returncode:
                stderr.seek(0)
                reason = stderr.read().decode('utf-8', 'replace').strip()[-2000:]
                _logger.warning('fork-sandbox adopt %s exited %s: %s', handle, process.returncode, reason)
            stderr.close()

    def _peek(self, handle, file=None, after=0):
        """Live transcript bytes for an in-flight cluster run (see the class
        docstring): (bytes, file name, next offset). Only present when the
        backend runs with --k8s."""
        argv = [self.executable, 'k8s', 'peek', str(handle), '--after', str(after)]
        if file:
            argv += ['--file', file]
        try:
            result = subprocess.run(argv, capture_output=True, timeout=_PEEK_TIMEOUT)
        except subprocess.TimeoutExpired:
            raise ValueError(f'fork-sandbox k8s peek timed out after {_PEEK_TIMEOUT}s') from None
        if result.returncode:
            reason = result.stderr.decode('utf-8', 'replace').strip().splitlines()
            raise ValueError(f'fork-sandbox k8s peek exited {result.returncode}: '
                              f'{reason[-1] if reason else "no output"}')
        stderr = result.stderr.decode('utf-8', 'replace').strip()
        if not stderr and not result.stdout:
            return b'', file, after  # pod/transcript not there yet: not an error, just nothing new
        status = stderr.splitlines()[-1] if stderr else ''
        m = _PEEK_STATUS.match(status)
        if not m:
            raise ValueError(f'fork-sandbox k8s peek: unparseable status line {status!r}')
        return result.stdout, m.group(1), int(m.group(2))


class FakeBackend(AgentBackend):
    """Persistent demo runner: after delay, append a scripted Python change.
    change defaults to a visible background tint overlay, inside the film.
    Pass `questions` (a list of {"text", "choices"} dicts, 1-3 of them) to make
    it ask instead of building: it replies with a ```questions block and
    commits nothing, as a real builder would when a note is unclear.
    Pass `shortfalls` (a list of {"kind", "what"} dicts, 1-5 of them) to add a
    ```shortfalls block to the reply, as a real builder would when a request
    falls short; it is added either way, whether or not `questions` is also set.
    Pass `cost_usd` and/or `tokens` to have the reply report them, as a real
    backend would through `status --json`; left unset, both stay null on the
    note, exactly as an unreporting backend leaves them.
    """
    name = 'fake'

    def __init__(self, delay=3, change=None, commits=1, extra_path=None, questions=None, lead_in=None,
                shortfalls=None, cost_usd=None, tokens=None):
        self.delay = delay
        self.commits = commits
        self.extra_path = extra_path
        self.questions = questions
        self.lead_in = lead_in if lead_in is not None else 'Quick check before I start:'
        self.shortfalls = shortfalls
        self.cost_usd = cost_usd
        self.tokens = tokens
        # The default argument binds the draw this change wraps, so applying it
        # again (commits > 1) wraps the previous one instead of recursing forever.
        self.change = change or ('\n'
                                'def _draft_draw(n, cv, _original_draw=FILM.draw):\n'
                                '    _original_draw(n, cv)\n'
                                '    cv.rect(0, 0, cv.width, 18, "#ffb547")\n'
                                'FILM.draw = _draft_draw\n')

    def submit(self, note):
        path = Path(note['state_dir']) / (note['id'] + '.fake.json')
        if not path.exists():
            path.write_text(json.dumps(dict(note=note, ready=time.time() + self.delay)))
        return str(path)

    def poll(self, handle):
        from .drafts import git
        path = Path(handle)
        data = json.loads(path.read_text())
        if 'result' in data:
            return AgentStatus(**data['result'])
        if time.time() < data['ready']:
            return AgentStatus('working')
        note = data['note']
        shortfalls_block = (f'```shortfalls\n{json.dumps({"shortfalls": self.shortfalls})}\n```\n\n'
                           if self.shortfalls else '')
        if self.questions:
            reply = (f'{self.lead_in}\n\n{shortfalls_block}'
                    f'```questions\n{json.dumps({"questions": self.questions})}\n```\n')
            result = AgentStatus('replied', reply, None, self.cost_usd, self.tokens)
            data['result'] = asdict(result)
            path.write_text(json.dumps(data))
            return result
        root = note['project']
        branch = note['draft'] or 'vb-draft/' + note['session'] + '-' + note['id']
        work = Path(note['state_dir']) / 'fake-work'
        if not note['draft']:
            git(root, 'branch', branch, 'main')
        git(root, 'worktree', 'add', str(work), branch)
        try:
            film = work / note['film']
            for number in range(self.commits):
                film.write_text(film.read_text() + self.change)
                git(work, 'add', '--', note['film'])
                git(work, '-c', 'user.name=Demo agent', '-c', 'user.email=agent@example.com',
                    'commit', '-qm', 'agent: ' + note['text'].splitlines()[0])
            if self.extra_path:
                target = work / self.extra_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('out of scope')
                git(work, 'add', '--', self.extra_path)
                git(work, '-c', 'user.name=Demo agent', '-c', 'user.email=agent@example.com',
                    'commit', '-qm', 'outside change')
        finally:
            git(root, 'worktree', 'remove', '--force', str(work))
        reply = 'Added an amber bar at the top of the frame for review.'
        if shortfalls_block:
            reply += '\n\n' + shortfalls_block.rstrip('\n')
        result = AgentStatus('replied', reply, branch, self.cost_usd, self.tokens)
        data['result'] = asdict(result)
        path.write_text(json.dumps(data))
        return result


def backend_from_config(config):
    cfg = dict(config)
    name = cfg.pop('backend', 'null')
    if name == 'null':
        return NullBackend()
    if name == 'fake':
        return FakeBackend(delay=cfg.get('delay', 3), cost_usd=cfg.get('cost_usd'), tokens=cfg.get('tokens'))
    if name == 'command':
        return CommandBackend(cfg.get('submit_command'), cfg.get('poll_command'))
    if name == 'fork-sandbox':
        return ForkSandboxBackend(**{k: v for k, v in cfg.items()
                                     if k in ('executable', 'submit_args', 'poll_args', 'extra_args',
                                              'context_root', 'context_mount', 'videobuilder_repo')})
    raise ValueError(f'unknown agent backend {name!r}')
