"""On-demand poster-frame thumbnails for the library grid: a small, letterboxed
JPEG grabbed from a video's latest finished render on main. Cached on disk
keyed by the commit *and* format it came from, in a tree separate from
Renders.root, so Renders.evict() dropping the render it was grabbed from
never invalidates it."""
from pathlib import Path
import subprocess
import threading

from .gitutil import git

WIDTH, HEIGHT = 640, 360
_LETTERBOX = (f'scale=w={WIDTH}:h={HEIGHT}:force_original_aspect_ratio=decrease,'
             f'pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=black')

# Guards concurrent ffmpeg grabs: shared across videos rather than per-editor,
# since a frame grab is rare and cheap enough that the coarser granularity
# never matters, and `from_state_dir` below has no editor to hang a lock off.
_LOCK = threading.Lock()

AMBIGUOUS = object()  # from_state_dir(): more than one video has ever rendered; ask the real editor


def _duration(path):
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                             '-of', 'default=noprint_wrappers=1:nokey=1', str(path)],
                            capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def _grab_frame(mp4_path, out_jpg):
    """The frame at 1.5s, or the middle for a render under 3s, letterboxed into
    a 16:9 JPEG regardless of the render's own aspect ratio."""
    duration = _duration(mp4_path)
    at = duration / 2 if duration < 3 else 1.5
    tmp = out_jpg.with_suffix('.jpg.partial')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{at:.3f}', '-i', str(mp4_path),
                    '-frames:v', '1', '-vf', _LETTERBOX, '-q:v', '4', '-f', 'image2', str(tmp)], check=True)
    tmp.replace(out_jpg)


def _by_sha(dir_path, suffix):
    """{sha: {fmt: path}} for every `<sha>-<fmt><suffix>` file in `dir_path`,
    read with one directory listing instead of one glob per commit."""
    out = {}
    for p in dir_path.glob(f'*{suffix}'):
        sha, _, fmt = p.name[:-len(suffix)].partition('-')
        out.setdefault(sha, {})[fmt] = p
    return out


def _answer(cache_dir, render_dir, shas):
    """Walk `shas` (newest-first) for the first commit with either a cached
    thumbnail or a finished render, preferring 16:9: a cached 16:9 JPEG, else
    a 16:9 render to grab one from, else whatever's already cached or
    rendered in another format. None once neither exists for any of `shas`."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached_by_sha = _by_sha(cache_dir, '.jpg')
    rendered_by_sha = _by_sha(render_dir, '.mp4')
    for sha in shas:
        cached, rendered = cached_by_sha.get(sha, {}), rendered_by_sha.get(sha, {})
        if not cached and not rendered:
            continue
        if '16x9' in cached:
            return cached['16x9'].read_bytes()
        if '16x9' in rendered:
            out = cache_dir / f'{sha}-16x9.jpg'
            with _LOCK:
                if not out.is_file():
                    _grab_frame(rendered['16x9'], out)
            return out.read_bytes()
        if cached:
            return next(iter(cached.values())).read_bytes()
        fmt, mp4_path = next(iter(rendered.items()))
        out = cache_dir / f'{sha}-{fmt}.jpg'
        with _LOCK:
            if not out.is_file():
                _grab_frame(mp4_path, out)
        return out.read_bytes()
    return None


class Thumbnails:
    def __init__(self, editor):
        self.editor = editor
        self.root = Path(editor.state_dir) / 'thumbnails'
        self.root.mkdir(parents=True, exist_ok=True)

    def _dir(self, video):
        slug = self.editor.notes.session_dir(video).name
        path = self.root / slug
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get(self, video):
        """JPEG bytes of the newest commit on main with a thumbnail to serve;
        None once neither a cached one nor a finished render exists yet (a
        brand new video, or one still rendering)."""
        result = git(self.editor.root, 'rev-list', '--first-parent', 'main', check=False)
        if result.returncode:
            return None
        render_dir = self.editor.renders.path(video, 'x' * 40, 'x').parent
        return _answer(self._dir(video), render_dir, result.stdout.split())


def from_state_dir(state_dir, repo_path):
    """The same answer as `Thumbnails.get`, straight off `state_dir` and the
    bare repo at `repo_path`, for a video whose Editor isn't already
    resident -- building one just to answer a thumbnail request would clone
    the repo and start its render-polling thread for nothing. The video id
    needed to find its slug (Thumbnails._dir) isn't known without an Editor
    to ask the project file for it, so this instead discovers whichever slug
    directories already exist on disk: unambiguous for the common case of one
    rendered video per project. Returns None with nothing to serve, or
    AMBIGUOUS if more than one video has ever rendered here and the caller
    should fall back to the real editor, which knows the video id."""
    state_dir = Path(state_dir)
    thumbs_root, renders_root = state_dir / 'thumbnails', state_dir / 'renders'
    slugs = {p.name for p in thumbs_root.glob('*') if p.is_dir()}
    slugs |= {p.name for p in renders_root.glob('*') if p.is_dir()}
    if not slugs:
        return None
    if len(slugs) > 1:
        return AMBIGUOUS
    slug = next(iter(slugs))
    result = git(None, 'rev-list', '--first-parent', 'main', git_dir=repo_path, hooks=False, check=False)
    if result.returncode:
        return None
    return _answer(thumbs_root / slug, renders_root / slug, result.stdout.split())
