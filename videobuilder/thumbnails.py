"""On-demand poster-frame thumbnails for the library grid: a small, letterboxed
JPEG grabbed from a video's latest finished render on main. Cached on disk
keyed by the commit it came from, in a tree separate from Renders.root, so
Renders.evict() dropping the render it was grabbed from never invalidates it."""
from pathlib import Path
import subprocess
import threading

from .gitutil import git

WIDTH, HEIGHT = 640, 360
_LETTERBOX = (f'scale=w={WIDTH}:h={HEIGHT}:force_original_aspect_ratio=decrease,'
             f'pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=black')


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


class Thumbnails:
    def __init__(self, editor):
        self.editor = editor
        self.root = Path(editor.state_dir) / 'thumbnails'
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()

    def _dir(self, video):
        slug = self.editor.notes.session_dir(video).name
        path = self.root / slug
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get(self, video):
        """JPEG bytes of the newest commit on main with either a cached
        thumbnail already or a finished render to grab one from (preferring
        16x9); None once neither exists yet (a brand new video, or one still
        rendering). Checking the cache before the render directory, per
        commit, newest first, is what lets an already-made thumbnail keep
        serving once Renders.evict() has removed the render it came from."""
        result = git(self.editor.root, 'rev-list', '--first-parent', 'main', check=False)
        if result.returncode:
            return None
        cache_dir = self._dir(video)
        render_dir = self.editor.renders.path(video, 'x' * 40, 'x').parent
        for sha in result.stdout.split():
            cached = cache_dir / f'{sha}.jpg'
            if cached.is_file():
                return cached.read_bytes()
            candidates = {p.stem.split('-', 1)[1]: p for p in render_dir.glob(f'{sha}-*.mp4')}
            if not candidates:
                continue
            mp4_path = candidates.get('16x9', next(iter(candidates.values())))
            with self.lock:
                if not cached.is_file():
                    _grab_frame(mp4_path, cached)
            return cached.read_bytes()
        return None
