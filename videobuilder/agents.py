"""Replaceable agent runners (stdlib only).

CommandBackend invokes ``submit_command + [request.json]`` and
``poll_command + [handle]`` without a shell. The request contains the note
fields plus project, film, image, note_file, state_dir, session and draft.
submit stdout is JSON {"handle": "opaque string"}; poll stdout is JSON
{"state": "queued|working|replied|failed", "reply": "text or null",
"branch": "local branch or null"}. Commands must be idempotent for a note
id: a crash between external submission and persisting its handle can retry.
The stable per-video state_dir is the runner's resumable session, and draft
is the current linear branch (null after Accept/Drop). Runners must honor it.

ForkSandboxBackend is deliberately isolated here: run --resume STATE
[--base DRAFT] [extra_args] PROJECT NOTE prints a run directory (--base only
when a draft exists; without it the run starts from main); status --json RUN prints
the status above, optionally reply_file (otherwise RUN/outbox/reply.md).
executable, submit_args, poll_args, extra_args are configurable argv lists
(executable is a string). No shell expansion is performed.
"""
import fcntl
import json
import re
import tempfile
import subprocess
import time
from pathlib import Path

from .notes import AgentBackend, AgentStatus, NullBackend
from .workers import pin_for, pinned_version


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
        if self.context_root and not self.context_root.is_relative_to(CONTEXT_STAGING_ROOT):
            raise ValueError(f"editor.agent.context_root must be under {CONTEXT_STAGING_ROOT}")

    def _context(self, note):
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
                    result = subprocess.run(['git', 'clone', '--depth', '1', '--branch', ref, url, str(staged)],
                                            capture_output=True, text=True)
                    if result.returncode:
                        raise ValueError('could not stage pinned videobuilder: ' + result.stderr.strip())
                    Path(temporary).rename(target)
        mount = self.context_mount or str(target)
        with open(note['note_file'], 'a', encoding='utf-8') as fh:
            fh.write(f"\nPinned videobuilder source: {mount}/videobuilder\n"
                     f"Use PYTHONPATH={mount}/videobuilder to render this video.\n"
                     f"Read {mount}/videobuilder/skill/make-a-video/SKILL.md.\n")
        return target

    def submit(self, note):
        context = self._context(note) if self.context_root else None
        base = ['--base', note['draft']] if note.get('draft') else []
        return run([self.executable, *self.submit_args, '--resume', note['state_dir'], *base,
                    *self.extra_args, *(['--context-ro', str(context)] if context else []),
                    *(['--attach-dir', note['attach_dir']] if note.get('attach_dir') else []),
                    note['project'], note['note_file']])

    def poll(self, handle):
        data = json.loads(run([self.executable, *self.poll_args, handle]))
        reply = data.get('reply')
        if data['state'] == 'replied' and reply is None:
            path = Path(data.get('reply_file') or Path(handle) / 'outbox/reply.md')
            if path.is_file():
                reply = path.read_text(encoding='utf-8')
        if reply:
            reply = re.sub(r'^== result:[^\n]*==\n+', '', reply)
        return AgentStatus(data['state'], reply, data.get('branch'))


class FakeBackend(AgentBackend):
    """Persistent demo runner: after delay, append a scripted Python change.
    change defaults to a visible background tint overlay, inside the film.
    """
    name = 'fake'

    def __init__(self, delay=3, change=None, commits=1, extra_path=None):
        self.delay = delay
        self.commits = commits
        self.extra_path = extra_path
        self.change = change or ('\n_original_draw = FILM.draw\n'
                                'def _draft_draw(n, cv):\n'
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
        result = AgentStatus('replied', 'Added an amber bar at the top of the frame for review.', branch)
        from dataclasses import asdict
        data['result'] = asdict(result)
        path.write_text(json.dumps(data))
        return result


def backend_from_config(config):
    cfg = dict(config)
    name = cfg.pop('backend', 'null')
    if name == 'null':
        return NullBackend()
    if name == 'fake':
        return FakeBackend(delay=cfg.get('delay', 3))
    if name == 'command':
        return CommandBackend(cfg.get('submit_command'), cfg.get('poll_command'))
    if name == 'fork-sandbox':
        return ForkSandboxBackend(**{k: v for k, v in cfg.items()
                                     if k in ('executable', 'submit_args', 'poll_args', 'extra_args',
                                              'context_root', 'context_mount', 'videobuilder_repo')})
    raise ValueError(f'unknown agent backend {name!r}')
