"""Serialized, sandboxed MP4 rendering for immutable commits.

A video is rendered whole, at a commit and in a format: `<sha>-<fmt>.mp4`. A
video whose commit has a timeline file (`timeline_file`) is a film made of
clips: its whole render is an assembly (`assembly.build`), its clip
directories rendered in the sandbox only when their content-keyed render
(`clip_cache`) isn't in `clips/` already. One clip's render can be asked for
on its own too (`request_clip`), keyed (video, sha, fmt, clip id) in the
same queue; it lands in the same content-keyed cache the assembly reads.
"""
from collections import deque
from pathlib import Path
import os
import signal
import shutil
import subprocess
import tempfile
import threading

from . import assembly, timeline_file
from .clip_cache import ClipCache, GitTree, clip_key, timeline_keys
from .drafts import git
from .workers import child_environment, sandbox_command

RENDER_LOCK = threading.Lock()


class Renders:
    def __init__(self, editor, jobs, keep, renderer=None):
        self.editor, self.jobs, self.keep = editor, jobs, keep
        self.renderer = renderer or self._render
        # (video, checkout, video root, clip, fmt, output): one clip directory's render.
        self.clip_renderer = self._render_clip
        self.root = Path(editor.state_dir) / 'renders'
        self.root.mkdir(parents=True, exist_ok=True)
        # A render killed with the process leaves its scratch behind, never a short .mp4:
        # output only ever appears by rename. The queue itself isn't kept; the player's
        # poll asks for the render again. Drafts.prune drops the stale worktree record.
        for stale in self.root.glob('render-*'):
            shutil.rmtree(stale, ignore_errors=True)
        for stale in self.root.glob('*/*.mp4.partial'):
            stale.unlink(missing_ok=True)
        for stale in self.root.glob('*/clips/*.partial.mp4'):
            stale.unlink(missing_ok=True)
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

    def clip_cache(self, video):
        return ClipCache(self.root / self.editor.notes.session_dir(video).name / 'clips')

    def _directory(self, video):
        return self.editor.drafts.context(video)['directory']

    def timeline(self, video, sha):
        """The video's `timeline_file.Timeline` at commit `sha`, or None when it
        has no timeline file there (a single film). Raises TimelineError."""
        directory = self._directory(video)
        data = GitTree(self.editor.root, sha, directory).read(timeline_file.NAME)
        if data is None:
            return None
        return timeline_file.loads(data.decode('utf-8', errors='replace'), timeline_file.NAME)

    def formats(self, video, sha):
        """The format names the video renders in at `sha`: its timeline's, or its film's."""
        try:
            timeline = self.timeline(video, sha)
        except ValueError:
            return []
        if timeline is not None:
            return list(timeline.formats)
        try:
            return [f['name'] for f in self.editor.info(video)['formats']]
        except (ValueError, KeyError):
            return []

    def clip_path(self, video, sha, fmt, clip_id):
        """Where clip `clip_id`'s render at `sha` in `fmt` is (or will be) cached.
        Raises KeyError for no such clip directory, ValueError for a bad timeline."""
        timeline = self.timeline(video, sha)
        clip = timeline.clip(clip_id) if timeline else None
        if clip is None or clip.is_footage:
            raise KeyError(clip_id)
        key = clip_key(GitTree(self.editor.root, sha, self._directory(video)), clip, fmt)
        return self.clip_cache(video).path(key, fmt)

    def output(self, key):
        """The file a queue key renders to: a whole video, or one clip."""
        return self.clip_path(*key) if len(key) == 4 else self.path(*key)

    def states(self, video, sha):
        return {fmt: self.state(video, sha, fmt)['state'] for fmt in self.formats(video, sha)}

    def state(self, video, sha, fmt, clip=None):
        key = (video, sha, fmt) if clip is None else (video, sha, fmt, clip)
        with self.lock:
            if self.output(key).is_file():
                return {'state': 'ready'}
            return self.status.get(key, {'state': 'none'})

    def request(self, video, sha, fmt, clip=None):
        """Queue the render of the video at `sha` in `fmt` (or of its one clip
        directory `clip`) unless it's ready or on its way; its state."""
        key = (video, sha, fmt) if clip is None else (video, sha, fmt, clip)
        with self.lock:
            state = self.state(*key)
            if state['state'] == 'none':
                self.queue.append(key)
                self.status[key] = {'state': 'queued'}
                state = self.status[key]
            position = list(self.queue).index(key) + 1 if key in self.queue else (1 if state['state'] == 'queued' else 0)
            return {**state, 'position': position}

    def request_clip(self, video, sha, fmt, clip):
        return self.request(video, sha, fmt, clip)

    def retry(self, video, sha, fmt, clip=None):
        key = (video, sha, fmt) if clip is None else (video, sha, fmt, clip)
        with self.lock:
            if self.status.get(key, {}).get('state') == 'failed':
                self.status.pop(key)
            return self.request(*key)

    def _loop(self):
        while not self.stopping.is_set():
            with self.lock:
                key = self.queue.popleft() if self.queue else None
            if key is None:
                self.stopping.wait(0.1)
                continue
            video, sha, fmt = key[:3]
            try:
                output = self.output(key)
            except (KeyError, ValueError) as exc:
                with self.lock:
                    self.status[key] = {'state': 'failed', 'error': 'render failed', 'log': str(exc)[-3000:]}
                continue
            output.parent.mkdir(parents=True, exist_ok=True)
            # A clip's partial keeps .mp4 last: ffmpeg picks the container from it.
            partial = (output.with_name(output.stem + '.partial.mp4') if len(key) == 4
                       else output.with_suffix('.mp4.partial'))
            try:
                while not self.stopping.is_set() and not RENDER_LOCK.acquire(timeout=0.2):
                    pass
                if self.stopping.is_set():
                    return
                try:
                    with self.lock:
                        self.active = key
                        self.status[key] = {'state': 'rendering'}
                    # A clip's render is content-keyed: an assembly or the same clip at another
                    # commit, queued ahead of it, may have made it while it waited.
                    if not output.is_file():
                        if len(key) == 4:
                            self._render_one_clip(video, sha, fmt, key[3], partial)
                        else:
                            self.renderer(video, sha, fmt, partial)
                        os.replace(partial, output)
                finally:
                    RENDER_LOCK.release()
                with self.lock:
                    self.status.pop(key, None)
                self.evict(video, sha)
            except Exception as exc:
                partial.unlink(missing_ok=True)
                if self.stopping.is_set():
                    # Cut off by shutdown, not failed: a drain-time poll still reads 'rendering'.
                    return
                with self.lock:
                    self.status[key] = {'state': 'failed', 'error': 'render failed', 'log': str(exc)[-3000:]}
            finally:
                with self.lock:
                    self.active = None

    def _checkout(self, sha, tmp):
        """(a worktree of `sha`, a scratch home) in `tmp`; the caller removes
        the worktree, and links the video's sources in."""
        work, home = Path(tmp) / 'checkout', Path(tmp) / 'output'
        home.mkdir()
        git(self.editor.root, 'worktree', 'add', '--detach', str(work), sha)
        return work, home

    def _render(self, video, sha, fmt, output):
        e = self.editor
        context = e.drafts.context(video)
        timeline = self.timeline(video, sha)
        with tempfile.TemporaryDirectory(prefix='render-', dir=self.root) as tmp:
            work, home = self._checkout(sha, tmp)
            try:
                e.sources.sync(video, root=work)
                if timeline is not None:
                    self._assemble(video, sha, fmt, output, timeline, work, home / 'assembly.mp4')
                    return
                film = work / context['film']
                name = output.name.removesuffix('.partial')
                self._sandboxed_render(film, work, home, fmt, name)
                shutil.copyfile(home / name, output)
            finally:
                git(e.root, 'worktree', 'remove', '--force', str(work))

    def _assemble(self, video, sha, fmt, output, timeline, work, scratch):
        directory = self._directory(video)
        root = work / directory
        tree = GitTree(self.editor.root, sha, directory)
        render_clip = lambda clip, f, dest: self.clip_renderer(video, work, root, clip, f, dest)
        with tempfile.TemporaryFile('w+') as log:
            assembly.build(timeline, fmt, scratch, root, tree, self.clip_cache(video), render_clip, log=log)
        shutil.copyfile(scratch, output)

    def _render_one_clip(self, video, sha, fmt, clip_id, output):
        timeline = self.timeline(video, sha)
        clip = timeline.clip(clip_id)
        with tempfile.TemporaryDirectory(prefix='render-', dir=self.root) as tmp:
            work, _ = self._checkout(sha, tmp)
            try:
                self.editor.sources.sync(video, root=work)
                self.clip_renderer(video, work, work / self._directory(video), clip, fmt, output)
            finally:
                git(self.editor.root, 'worktree', 'remove', '--force', str(work))

    def _render_clip(self, video, work, root, clip, fmt, output):
        """Render one clip directory in the sandbox, its video's root on the
        import path so it can import `shared`."""
        # render-: the startup sweep clears it if the editor dies mid-render.
        with tempfile.TemporaryDirectory(prefix='render-clip-', dir=self.root) as home:
            name = f'{clip.id}-{fmt}.mp4'
            self._sandboxed_render(root / clip.film_path, work, Path(home), fmt, name, path=root)
            shutil.copyfile(Path(home) / name, output)

    def _sandboxed_render(self, film, work, home, fmt, name, path=None):
        """`videobuilder render` of `film` in the checkout `work`, in the
        sandbox, to `home/name`; `path` goes on the film's import path."""
        python, key, _ = self.editor.envs.python(film, work)
        source = Path(__file__).resolve().parent.parent if key == 'current' else None
        command = sandbox_command(python, work, home, source=source, command=[
            python, '-m', 'videobuilder', 'render', str(film), '--format', fmt,
            '--out', str(home / name), '--jobs', str(self.jobs)])
        env = child_environment(home, source)
        if path is not None:
            env['PYTHONPATH'] = os.pathsep.join(p for p in (str(path), env.get('PYTHONPATH')) if p)
        with tempfile.TemporaryFile() as log:
            proc = subprocess.Popen(command, cwd=home, env=env, stdout=log, stderr=log, start_new_session=True)
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

    def evict(self, video, preserve=None):
        recent = git(self.editor.root, 'rev-list', '--first-parent', f'--max-count={self.keep}', 'main').splitlines()
        if preserve and preserve not in recent:
            recent = recent[:max(0, self.keep - 1)] + [preserve]
        commits = set(recent)
        directory = self.path(video, 'x' * 40, 'x').parent
        for path in directory.glob('*.mp4'):
            if path.name[:40] not in commits:
                path.unlink(missing_ok=True)
        if (directory / 'clips').is_dir():
            # Keep every clip render the kept commits' timelines use, in any format.
            keep = set()
            for sha in commits:
                try:
                    timeline = self.timeline(video, sha)
                except ValueError:
                    continue
                if timeline is not None:
                    keep |= timeline_keys(timeline, GitTree(self.editor.root, sha, self._directory(video)))
            self.clip_cache(video).evict(keep)

    def close(self):
        self.stopping.set()
        self.thread.join(timeout=10)
