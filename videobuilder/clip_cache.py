"""Clip renders keyed by what goes into them, not by commit.

A clip directory's render key is a hash of its inputs: the clip directory's
content, the video's `shared/` directory (code any clip may import, as
`from shared import ...`; the repo root is on the clip's import path), the
video's `requirements.txt` (the pinned videobuilder), the film file's name and
the format. A commit that leaves those alone leaves the key alone, so the
clip's MP4 is reused; an edit to the clip, to `shared/` or to the pin changes
it. Footage clips have no key: they are never rendered, only cut.

Not in the key: the video's uploaded `sources/`. A clip that reads a source
reads it by name, and a source's name is never reused for different content
while it exists (an upload refuses a name already taken; delete and upload
again under the same name is the one way to go stale, until the clip changes).

Two ways to read the inputs, giving keys from the same recipe:
  - `GitTree(repo, sha)`: git tree and blob ids at a commit (the editor);
  - `FileTree(root)`: a hash of the files on disk (`assemble` on a working
    directory, committed or not).
"""
import hashlib
import os
import subprocess
from pathlib import Path, PurePosixPath

SHARED = 'shared'
REQUIREMENTS = 'requirements.txt'
KEY_VERSION = 'clip-render-2'  # 2: a render keeps its Sound spans beside it
# Never part of a clip's content: build droppings, and the editor's synced sources.
_IGNORED_DIRS = {'__pycache__', 'sources', '.git'}
_IGNORED_SUFFIXES = ('.pyc',)


class GitTree:
    """Content ids at commit `sha` of the repo at `repo`, for the video in its
    directory `prefix` (paths are relative to that). The commit's listing is
    read once, on first use: one git call per commit, however many clips."""

    def __init__(self, repo, sha, prefix='.'):
        self.repo, self.sha = str(repo), sha
        self.prefix = '' if prefix in ('', '.') else prefix.strip('/') + '/'
        self._ids = None

    def _full(self, path):
        return self.prefix + str(PurePosixPath(path))

    def id(self, path):
        """The git object id of `path` at the commit, or None if it isn't there."""
        if self._ids is None:
            cmd = ['git', 'ls-tree', '-r', '-t', '-z', self.sha]
            if self.prefix:
                cmd += ['--', self.prefix]
            result = subprocess.run(cmd, cwd=self.repo, capture_output=True, text=True)
            if result.returncode:
                raise ValueError(f'cannot read commit {self.sha}: {result.stderr.strip()}')
            self._ids, self._blobs = {}, []
            for entry in filter(None, result.stdout.split('\0')):
                meta, name = entry.split('\t', 1)
                self._ids[name] = meta.split()[2]
                if meta.split()[1] == 'blob':
                    self._blobs.append(name)
        return self._ids.get(self._full(path))

    def files(self, path):
        """Every file under directory `path` at the commit, relative to the
        video's directory, sorted; [] when there is no such directory."""
        self.id(path)
        under = self._full(path).rstrip('/') + '/'
        return sorted(name[len(self.prefix):] for name in self._blobs if name.startswith(under))

    def read(self, path):
        """The bytes of `path` at the commit, or None."""
        result = subprocess.run(['git', 'show', f'{self.sha}:{self._full(path)}'], cwd=self.repo,
                                capture_output=True)
        return result.stdout if result.returncode == 0 else None


class FileTree:
    """Content ids of the files under `root` as they are on disk."""

    def __init__(self, root):
        self.root = Path(root)

    def id(self, path):
        p = self.root / path
        if p.is_file():
            return 'file:' + hashlib.sha256(p.read_bytes()).hexdigest()
        if not p.is_dir():
            return None
        h = hashlib.sha256()
        for d, dirs, files in os.walk(p):
            dirs[:] = sorted(x for x in dirs if x not in _IGNORED_DIRS and not x.startswith('.'))
            for f in sorted(files):
                if f.endswith(_IGNORED_SUFFIXES) or f.startswith('.'):
                    continue
                full = Path(d) / f
                h.update(full.relative_to(p).as_posix().encode() + b'\0')
                h.update(hashlib.sha256(full.read_bytes()).digest())
        return 'dir:' + h.hexdigest()

    def read(self, path):
        p = self.root / path
        return p.read_bytes() if p.is_file() else None


def clip_key(tree, clip, fmt):
    """The render key (40 hex digits) of clip directory `clip` in format `fmt`,
    read through `tree` (a GitTree or FileTree). Raises ValueError when the
    clip's directory or film file is missing."""
    clip_id = tree.id(clip.dir)
    if clip_id is None:
        raise ValueError(f'clip "{clip.id}": no directory {clip.dir}')
    if tree.id(clip.film_path) is None:
        raise ValueError(f'clip "{clip.id}": no film file {clip.film_path}')
    parts = [KEY_VERSION, f'clip {clip_id}', f'film {clip.film}', f'shared {tree.id(SHARED) or "-"}',
             f'requirements {tree.id(REQUIREMENTS) or "-"}', f'format {fmt}']
    return hashlib.sha256('\n'.join(parts).encode()).hexdigest()[:40]


def timeline_keys(timeline, tree, formats=None):
    """{render key} of every clip directory in `timeline`, in each of `formats`
    (default: the timeline's own), skipping clips whose files are missing."""
    keys = set()
    for fmt in formats or timeline.formats:
        for c in timeline.clips:
            if c.is_footage:
                continue
            try:
                keys.add(clip_key(tree, c, fmt))
            except ValueError:
                pass
    return keys


def spans_path(mp4):
    """The Sound spans sidecar of a clip render `mp4` (`x.mp4` -> `x.spans.json`):
    where its film's Sounds play, for an assembly's ducked lanes."""
    mp4 = Path(mp4)
    return mp4.with_name(mp4.name.removesuffix('.mp4') + '.spans.json')


def finish(partial, out):
    """Move a finished clip render `partial` and its spans sidecar, if it
    wrote one, into place at `out`: the sidecar first, so a whole MP4 always
    has its spans beside it."""
    if spans_path(partial).is_file():
        os.replace(spans_path(partial), spans_path(out))
    os.replace(partial, out)


def discard(partial):
    """Delete a clip render `partial` and its sidecar."""
    Path(partial).unlink(missing_ok=True)
    spans_path(partial).unlink(missing_ok=True)


class ClipCache:
    """`<root>/<key>-<format>.mp4`, written atomically: a render goes to
    `<key>-<format>.partial.mp4` (ffmpeg picks the container from the
    extension) and is renamed into place, so a finished name is always whole.
    Beside each, `<key>-<format>.spans.json` (`spans_path`), when the
    renderer wrote one."""

    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, key, fmt):
        return self.root / f'{key}-{fmt}.mp4'

    def get(self, key, fmt, render):
        """The cached MP4 for (key, fmt), rendering it first with
        `render(partial_path)` when there is none. Returns (path, rendered)."""
        out = self.path(key, fmt)
        if out.is_file():
            return out, False
        partial = out.with_name(f'{key}-{fmt}.partial.mp4')
        try:
            render(partial)
            finish(partial, out)
        finally:
            discard(partial)
        return out, True

    def evict(self, keep):
        """Delete every cached render whose key isn't in `keep`."""
        for p in [*self.root.glob('*.mp4'), *self.root.glob('*.spans.json')]:
            if p.name[:40] not in keep and '.partial.' not in p.name:
                p.unlink(missing_ok=True)

    def sweep_partials(self):
        """Delete what a render killed with its process left behind."""
        for p in self.root.glob('*.partial.mp4'):
            discard(p)
