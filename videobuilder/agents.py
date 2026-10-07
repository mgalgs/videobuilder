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
import json
import subprocess
import time
from pathlib import Path

from .notes import AgentBackend, AgentStatus, NullBackend


def run(argv):
    return subprocess.run(argv, capture_output=True, text=True, check=True, timeout=60).stdout.strip()


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


class ForkSandboxBackend(AgentBackend):
    name = 'fork-sandbox'

    def __init__(self, executable='fork-sandbox', submit_args=None, poll_args=None, extra_args=None):
        self.executable = executable
        self.submit_args = ['run'] if submit_args is None else submit_args
        self.poll_args = ['status', '--json'] if poll_args is None else poll_args
        self.extra_args = extra_args or []

    def submit(self, note):
        base = ['--base', note['draft']] if note.get('draft') else []
        return run([self.executable, *self.submit_args, '--resume', note['state_dir'], *base,
                    *self.extra_args, note['project'], note['note_file']])

    def poll(self, handle):
        data = json.loads(run([self.executable, *self.poll_args, handle]))
        reply = data.get('reply')
        if data['state'] == 'replied' and reply is None:
            path = Path(data.get('reply_file') or Path(handle) / 'outbox/reply.md')
            if path.is_file():
                reply = path.read_text(encoding='utf-8')
        return AgentStatus(data['state'], reply, data.get('branch'))


class FakeBackend(AgentBackend):
    """Persistent demo runner: after delay, append a scripted Python change.
    change defaults to a visible background tint overlay, inside the film.
    """
    name = 'fake'

    def __init__(self, delay=3, change=None):
        self.delay = delay
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
            film.write_text(film.read_text() + self.change)
            git(work, 'add', '--', note['film'])
            git(work, '-c', 'user.name=Demo agent', '-c', 'user.email=agent@example.com',
                'commit', '-qm', 'agent: ' + note['text'].splitlines()[0])
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
                                     if k in ('executable', 'submit_args', 'poll_args', 'extra_args')})
    raise ValueError(f'unknown agent backend {name!r}')
