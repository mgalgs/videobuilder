"""Serialized, sandboxed MP4 rendering for immutable commits."""
from collections import deque
from pathlib import Path
import os
import signal
import shutil
import subprocess
import tempfile
import threading

from .drafts import git
from .workers import child_environment, sandbox_command

RENDER_LOCK = threading.Lock()


class Renders:
    def __init__(self, editor, jobs, keep, renderer=None):
        self.editor, self.jobs, self.keep = editor, jobs, keep
        self.renderer = renderer or self._render
        self.root = Path(editor.state_dir) / 'renders'
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.queue = deque()
        self.status = {}
        self.active = None
        self.stopping = threading.Event()
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def path(self, video, sha, fmt):
        slug = self.editor.notes.session_dir(video).name
        return self.root / slug / f'{sha}-{fmt}.mp4'

    def states(self, video, sha):
        try:
            formats = [f['name'] for f in self.editor.info(video)['formats']]
        except (ValueError, KeyError):
            formats = []
        return {fmt: self.state(video, sha, fmt)['state'] for fmt in formats}

    def state(self, video, sha, fmt):
        key = (video, sha, fmt)
        with self.lock:
            if self.path(*key).is_file():
                return {'state': 'ready'}
            return self.status.get(key, {'state': 'none'})

    def request(self, video, sha, fmt):
        key = (video, sha, fmt)
        with self.lock:
            state = self.state(*key)
            if state['state'] == 'none':
                self.queue.append(key)
                self.status[key] = {'state': 'queued'}
                state = self.status[key]
            position = list(self.queue).index(key) + 1 if key in self.queue else (1 if state['state'] == 'queued' else 0)
            return {**state, 'position': position}

    def retry(self, video, sha, fmt):
        key = (video, sha, fmt)
        with self.lock:
            if self.status.get(key, {}).get('state') == 'failed':
                self.status.pop(key)
            return self.request(video, sha, fmt)

    def _loop(self):
        while not self.stopping.is_set():
            with self.lock:
                key = self.queue.popleft() if self.queue else None
            if key is None:
                self.stopping.wait(0.1)
                continue
            video, sha, fmt = key
            output = self.path(*key)
            output.parent.mkdir(parents=True, exist_ok=True)
            partial = output.with_suffix('.mp4.partial')
            try:
                while not self.stopping.is_set() and not RENDER_LOCK.acquire(timeout=0.2):
                    pass
                if self.stopping.is_set():
                    return
                try:
                    with self.lock:
                        self.active = key
                        self.status[key] = {'state': 'rendering'}
                    self.renderer(video, sha, fmt, partial)
                    os.replace(partial, output)
                finally:
                    RENDER_LOCK.release()
                with self.lock:
                    self.status.pop(key, None)
                self.evict(video, sha)
            except Exception as exc:
                partial.unlink(missing_ok=True)
                with self.lock:
                    self.status[key] = {'state': 'failed', 'error': 'render failed', 'log': str(exc)[-3000:]}
            finally:
                with self.lock:
                    self.active = None

    def _render(self, video, sha, fmt, output):
        e = self.editor
        context = e.drafts.context(video)
        with tempfile.TemporaryDirectory(prefix='render-', dir=self.root) as tmp:
            work = Path(tmp) / 'checkout'
            home = Path(tmp) / 'output'
            home.mkdir()
            git(e.root, 'worktree', 'add', '--detach', str(work), sha)
            try:
                e.sources.sync(video, root=work)
                film = work / context['film']
                python, key, _ = e.envs.python(film, work)
                source = Path(__file__).resolve().parent.parent if key == 'current' else None
                command = sandbox_command(python, work, home, source=source, command=[
                    python, '-m', 'videobuilder', 'render', str(film), '--format', fmt,
                    '--out', str(home / output.name.removesuffix('.partial')), '--jobs', str(self.jobs)])
                with tempfile.TemporaryFile() as log:
                    proc = subprocess.Popen(command, cwd=home, env=child_environment(home, source),
                                            stdout=log, stderr=log, start_new_session=True)
                    try:
                        while proc.poll() is None:
                            if self.stopping.wait(0.2):
                                os.killpg(proc.pid, signal.SIGKILL)
                                raise ValueError('render stopped')
                    finally:
                        if proc.poll() is None:
                            os.killpg(proc.pid, signal.SIGKILL)
                            proc.wait()
                    if proc.returncode:
                        log.seek(0)
                        raise ValueError(log.read().decode(errors='replace')[-3000:])
                shutil.copyfile(home / output.name.removesuffix('.partial'), output)
            finally:
                git(e.root, 'worktree', 'remove', '--force', str(work))

    def evict(self, video, preserve=None):
        recent = git(self.editor.root, 'rev-list', '--first-parent', f'--max-count={self.keep}', 'main').splitlines()
        if preserve and preserve not in recent:
            recent = recent[:max(0, self.keep - 1)] + [preserve]
        commits = set(recent)
        directory = self.path(video, 'x' * 40, 'x').parent
        for path in directory.glob('*.mp4'):
            if path.name[:40] not in commits:
                path.unlink(missing_ok=True)

    def close(self):
        self.stopping.set()
        self.thread.join(timeout=10)
