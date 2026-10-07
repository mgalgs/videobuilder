"""A project: a directory (usually a git repo) holding several videos, each a
film file in a directory of its own. The editor finds the videos, and turns
each direct edit into one git commit that touches only that film's edits file.

Finding videos. With a `videobuilder.toml` at the project's root that lists
them, exactly those:

    [editor]
    videos = ["launch/film.py", "promo/promo.py"]   # relative to the project
    state_dir = ".vb-editor"                        # optional, see editor.py

Otherwise every `*.py` file under the project that assigns a module-level
`FILM` and mentions `Timeline`, read without running it, skipping
dot-directories and `SKIP_DIRS`. A video's id is its path from the project
root without `.py` (`launch/film`); commit messages name it.

Committing. `Project.edit` writes the edit with `edits.roll` or
`edits.set_copy`, then commits that one path (`git commit -- <path>`) with
the author from git config. When the project is not in a git repo, or the
edits file already had uncommitted changes, the edit is still written, but
not committed, and the result carries a warning. Nothing is ever pushed.
"""
import ast
import os
import subprocess
import tempfile
import threading
import tomllib
from dataclasses import dataclass

from . import edits

CONFIG = 'videobuilder.toml'
SKIP_DIRS = {'tests', 'test', 'vendor', 'node_modules', '__pycache__', 'build', 'dist', 'venv', 'site-packages'}


@dataclass(frozen=True)
class Video:
    id: str      # 'launch/film': the path from the project root, without .py
    path: str    # absolute path of the film file

    def to_json(self, root):
        return {'id': self.id, 'path': os.path.relpath(self.path, root),
                'edits': os.path.relpath(edits.path_for(self.path), root)}


def read_config(root):
    """The `[editor]` table of `<root>/videobuilder.toml`, or {} without one."""
    path = os.path.join(root, CONFIG)
    try:
        with open(path, 'rb') as fh:
            doc = tomllib.load(fh)
    except FileNotFoundError:
        return {}
    except tomllib.TOMLDecodeError as e:
        raise ValueError(f'{path}: {e}') from None
    cfg = doc.get('editor', {})
    if not isinstance(cfg, dict):
        raise ValueError(f'{path}: editor must be a table')
    videos = cfg.get('videos')
    if videos is not None and not (isinstance(videos, list) and all(isinstance(v, str) for v in videos)):
        raise ValueError(f'{path}: editor.videos must be a list of film paths')
    if not isinstance(cfg.get('state_dir', ''), str):
        raise ValueError(f'{path}: editor.state_dir must be a path')
    return cfg


def looks_like_film(path):
    """Whether a .py file assigns a module-level FILM and mentions Timeline,
    read with `ast`, never run."""
    try:
        with open(path, 'rb') as fh:
            tree = ast.parse(fh.read(), path)
    except (OSError, SyntaxError, ValueError):
        return False
    film = False
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(
            node, ast.AnnAssign) else []
        film = film or any(isinstance(t, ast.Name) and t.id == 'FILM' for t in targets)
    if not film:
        return False
    return any((isinstance(n, ast.Name) and n.id == 'Timeline') or
               (isinstance(n, ast.Attribute) and n.attr == 'Timeline') for n in ast.walk(tree))


def discover(root, skip=()):
    """The videos under `root`, sorted by id: the ones `videobuilder.toml`
    lists, or else the film files found by `looks_like_film`. `skip` holds
    more absolute directories to leave out (the editor's state)."""
    root = os.path.abspath(root)
    listed = read_config(root).get('videos')
    if listed is not None:
        out = []
        for rel in listed:
            path = os.path.normpath(os.path.join(root, rel))
            if os.path.relpath(path, root).startswith('..'):
                raise ValueError(f'{CONFIG}: {rel} is outside the project')
            if not os.path.isfile(path):
                raise ValueError(f'{CONFIG}: {rel} does not exist')
            out.append(_video(root, path))
        return sorted(out, key=lambda v: v.id)
    skip = {os.path.abspath(s) for s in skip}
    out = []
    for d, dirs, files in os.walk(root):
        dirs[:] = sorted(x for x in dirs if not x.startswith('.') and x not in SKIP_DIRS
                         and os.path.join(d, x) not in skip)
        for f in sorted(files):
            if f.endswith('.py') and looks_like_film(os.path.join(d, f)):
                out.append(_video(root, os.path.join(d, f)))
    return sorted(out, key=lambda v: v.id)


def _video(root, path):
    rel = os.path.relpath(path, root)
    return Video(os.path.splitext(rel)[0].replace(os.sep, '/'), path)


# ---- git ----

def _git(cwd, *args):
    return subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True)


def git_root(path):
    """The top of the git work tree holding `path`, or None."""
    r = _git(path, 'rev-parse', '--show-toplevel')
    return os.path.abspath(r.stdout.strip()) if r.returncode == 0 else None


def git_state(root, path):
    """('none' | 'clean' | 'dirty' | 'ignored') of one file in the repo at `root`."""
    if root is None:
        return 'none'
    if _git(root, 'check-ignore', '-q', '--', path).returncode == 0:
        return 'ignored'
    r = _git(root, 'status', '--porcelain', '--untracked-files=all', '--', path)
    return 'dirty' if r.stdout.strip() else 'clean'


def commit_path(root, path, message):
    """Commit the one file `path` (added first when untracked) with `message`.
    Returns the new commit's sha. Raises RuntimeError, leaving the index as
    it was, if git refuses."""
    tracked = _git(root, 'ls-files', '--error-unmatch', '--', path).returncode == 0
    if not tracked:
        r = _git(root, 'add', '--', path)
        if r.returncode:
            raise RuntimeError(r.stderr.strip() or 'git add failed')
    r = _git(root, 'commit', '--quiet', '-m', message, '--', path)
    if r.returncode:
        if not tracked:
            _git(root, 'rm', '--cached', '--quiet', '--', path)
        raise RuntimeError(r.stderr.strip() or r.stdout.strip() or 'git commit failed')
    return _git(root, 'rev-parse', 'HEAD').stdout.strip()


def beats(x):
    return f'{x:g}'


class Project:
    """The videos under `root`, and the edit-and-commit flow. `lock` is held
    around every film load (imports and Pango are not thread-safe); share it
    with anything else that loads films."""

    def __init__(self, root, skip=(), lock=None, worker=None):
        self.root = os.path.abspath(root)
        if not os.path.isdir(self.root):
            raise ValueError(f'{root} is not a directory')
        self.skip = tuple(skip)
        self.lock = lock or threading.RLock()
        self.worker = worker
        self.git = git_root(self.root)
        self.last = {}  # video id -> the inverse of the last edit made here, for undo
        self.seen = {}  # video id -> Video, so a film mid-edit with a syntax error stays listed

    def videos(self):
        """The videos found now, and any found before whose file still exists."""
        found = discover(self.root, self.skip)
        if read_config(self.root).get('videos') is not None:
            self.seen = {v.id: v for v in found}  # the list is the truth
            return found
        for v in found:
            self.seen[v.id] = v
        self.seen = {k: v for k, v in self.seen.items() if os.path.isfile(v.path)}
        return sorted(self.seen.values(), key=lambda v: v.id)

    def video(self, vid):
        """The video `vid`: from the last look while its file exists (this is
        asked on every frame), else from a fresh one. Raises KeyError."""
        v = self.seen.get(vid)
        if v is not None and os.path.isfile(v.path):
            return v
        for v in self.videos():
            if v.id == vid:
                return v
        raise KeyError(vid)

    def _current(self, video, op, segment, key):
        """The segment's value now, with every edit in place."""
        try:
            s = edits.timeline(video.path).find(segment)
        except KeyError:
            raise ValueError(f'no segment named {segment!r} in the timeline') from None
        if op == 'roll':
            return s.until
        if key not in s.data:
            raise ValueError(f'segment {segment}: data has no key {key!r} to override')
        return s.data[key]

    def edit(self, vid, op, segment, value, key=None, undo=False):
        """Apply one direct edit to video `vid` and commit it: `op` 'roll'
        (`value`: the new end in beats) or 'copy' (`key`, and the new string).
        Returns a dict: `message`, `commit` (sha or None), `warning` (or None),
        `changed`, and `undo` (the edit that reverses this one). Raises
        ValueError, leaving the file and the repo alone, when refused."""
        video = self.video(vid)
        path = edits.path_for(video.path)
        if op == 'roll':
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f'until must be a number of beats, not {value!r}')
            message = f'edit({vid}): roll {segment} to beat {beats(value)}'
        elif op == 'copy':
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError('a copy edit needs a key and a string value')
            message = f'edit({vid}): copy {segment}.{key}'
        else:
            raise ValueError(f'unknown edit {op!r}')
        if undo:
            message += ' (undo)'
        with self.lock:
            try:
                before = self._current(video, op, segment, key) if self.worker is None else None
                state = git_state(self.git, path)
                old = _read(path)
                if self.worker is not None:
                    response = self.worker(vid).request('edit', segment=segment,
                                                        field='until' if op == 'roll' else 'data',
                                                        key=key, value=value)
                    before = response['before']
                    if response['toml']:
                        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=os.path.dirname(path),
                                                         delete=False) as output:
                            output.write(response['toml'])
                            temporary = output.name
                        os.replace(temporary, path)
                    elif os.path.exists(path):
                        os.remove(path)
                elif op == 'roll':
                    edits.roll(video.path, segment, value)
                else:
                    edits.set_copy(video.path, segment, key, value)
            except ValueError:
                raise
            except Exception as e:  # the film itself doesn't load: nothing was written
                raise ValueError(f'{vid} does not load ({type(e).__name__}: {e}); fix it before editing') from e
            changed = _read(path) != old
            commit = warning = None
            if not changed:
                pass
            elif state == 'none':
                warning = 'not a git repository: the edit is saved but not committed'
            elif state == 'dirty':
                warning = (f'{os.path.relpath(path, self.root)} had uncommitted changes from outside the editor: '
                           'the edit is saved but not committed')
            elif state == 'ignored':
                warning = f'{os.path.relpath(path, self.root)} is git-ignored: the edit is saved but not committed'
            else:
                try:
                    commit = commit_path(self.git, path, message)
                except RuntimeError as e:
                    warning = f'the edit is saved, but git would not commit it: {e}'
            inverse = {'op': op, 'segment': segment, 'value': before}
            if key is not None:
                inverse['key'] = key
            if changed:
                self.last[vid] = None if undo else inverse
            return {'message': message, 'commit': commit, 'warning': warning, 'changed': changed,
                    'undo': self.last.get(vid)}

    def undo(self, vid):
        """Reverse the last edit made to `vid` through this Project, as a new
        edit (and commit). Raises ValueError when there is none, or it is
        refused now."""
        inverse = self.last.get(vid)
        if not inverse:
            raise ValueError('nothing to undo')
        return self.edit(vid, inverse['op'], inverse['segment'], inverse['value'], inverse.get('key'), undo=True)

    def git_info(self, vid):
        path = edits.path_for(self.video(vid).path)
        return {'repo': self.git is not None, 'state': git_state(self.git, path)}


def _read(path):
    try:
        with open(path, 'rb') as fh:
            return fh.read()
    except FileNotFoundError:
        return None
