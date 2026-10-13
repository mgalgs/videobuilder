"""Small, engine-independent cache for sequentially rendered RGBA shots.

Build explicitly before rendering a film. draw() only reads complete PNGs, so
arbitrary frame order and parallel workers never launch a renderer.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

from PIL import Image as PILImage

from .canvas import Image


def cache_key(source, size, fps, frames):
    """Hash source bytes and render parameters; source is a file or bytes."""
    source = Path(source).read_bytes() if isinstance(source, (str, os.PathLike)) else source
    spec = json.dumps([list(size), fps, frames], separators=(',', ':')).encode()
    return hashlib.sha256(source + b'\0' + spec).hexdigest()[:20]


class ShotCache:
    def __init__(self, root, source, size, fps, frames):
        self.size = tuple(size)
        self.fps = fps
        self.frames = frames
        self.path = Path(root) / cache_key(source, size, fps, frames)

    def build(self, source):
        """Consume (index, RGBA bytes) in order; publish only a complete shot."""
        if (self.path / 'complete').exists():
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(tempfile.mkdtemp(prefix='.shot-', dir=self.path.parent))
        try:
            expected = 0
            for index, rgba in source():
                if index != expected or index >= self.frames:
                    raise ValueError(f'expected frame {expected}, got {index}')
                image = PILImage.frombytes('RGBA', self.size, rgba)
                image.save(tmp / f'{index:05d}.png')
                expected += 1
            if expected != self.frames:
                raise ValueError(f'expected {self.frames} frames, got {expected}')
            (tmp / 'complete').write_text('ok\n')
            if self.path.exists():
                shutil.rmtree(self.path)  # incomplete build from an earlier attempt
            os.replace(tmp, self.path)
        finally:
            if tmp.exists():
                shutil.rmtree(tmp)
        return True

    def image(self, index):
        if not (self.path / 'complete').exists():
            raise FileNotFoundError(f'build shot cache first: {self.path}')
        if not 0 <= index < self.frames:
            raise IndexError(index)
        # These frames are usually read once; avoid Image.load's unbounded cache.
        with PILImage.open(self.path / f'{index:05d}.png') as pil:
            return Image.from_pil(pil)
