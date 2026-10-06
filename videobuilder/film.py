"""What a film file defines, and how it is loaded.

A film file is a Python module with a module-level `FILM`:

    FILM = Film(draw=draw, fps=30, frames=90, formats=('9x16', '16x9', '1x1'))

`draw(n, canvas)` paints frame `n` and must be a pure function of `n` (and of
`canvas.format`): any frame, chunk or format renders alone, in any order.
"""
import importlib.util
import itertools
import os
import sys
from dataclasses import dataclass
from typing import Callable

from .canvas import Canvas
from .timeline import Timeline


@dataclass(frozen=True)
class Format:
    """An output size. Formats are layouts, not crops: `draw` sees which one it
    is drawing (`canvas.format`) and lays the frame out for it."""
    name: str
    width: int
    height: int

    @property
    def aspect(self):
        return self.width / self.height

    @property
    def portrait(self):
        return self.height > self.width

    @property
    def landscape(self):
        return self.width > self.height

    @property
    def square(self):
        return self.width == self.height

    def __str__(self):
        return self.name


FORMATS = {f.name: f for f in (
    Format('9x16', 1080, 1920),
    Format('16x9', 1920, 1080),
    Format('1x1', 1080, 1080),
)}


def as_format(f):
    if isinstance(f, Format):
        return f
    try:
        return FORMATS[f]
    except KeyError:
        raise ValueError(f'unknown format {f!r}; known: {", ".join(FORMATS)}') from None


@dataclass
class Audio:
    path: str
    trim_frames: int = 0  # skipped at the head of the file
    gain_db: float = 0.0
    fade_out_frames: int = 0  # linear fade reaching silence on the last frame


@dataclass
class Film:
    """A film: a pure draw function plus its timing and formats.

    `frames` and `fps` may be left out when a `timeline` gives them. The first
    of `formats` is the default; each is a name from `FORMATS` or a `Format`.
    """
    draw: Callable[[int, Canvas], None]
    fps: int | None = None
    frames: int | None = None
    formats: tuple = ('16x9',)
    background: str | tuple | None = '#000000'
    audio: Audio | None = None
    timeline: Timeline | None = None
    # Frames worth reviewing, as frame numbers or (frame, label) pairs: the
    # default frames of `sheet`, labelled. Checks can walk them too.
    keyframes: tuple = ()

    def __post_init__(self):
        if self.timeline is not None:
            tl_fps = self.timeline.grid.fps
            if self.fps is not None and self.fps != tl_fps:
                raise ValueError(f'fps {self.fps} != timeline fps {tl_fps}')
            self.fps = tl_fps
            if self.frames is None:
                self.frames = self.timeline.frames
        if self.fps is None or self.frames is None:
            raise ValueError('Film needs fps and frames (or a timeline)')
        if isinstance(self.formats, (str, Format)):
            self.formats = (self.formats,)
        self.formats = tuple(as_format(f) for f in self.formats)
        if not self.formats:
            raise ValueError('Film needs at least one format')
        keys = []
        for k in self.keyframes:
            n, label = (k, '') if isinstance(k, int) else k
            if not 0 <= n < self.frames:
                raise ValueError(f'keyframe {n} ({label}) outside 0..{self.frames - 1}')
            keys.append((n, label))
        self.keyframes = tuple(keys)

    def format(self, name=None):
        """The `Format` called `name` (default: the film's first)."""
        if name is None:
            return self.formats[0]
        key = getattr(name, 'name', name)
        for f in self.formats:
            if f.name == key:
                return f
        raise ValueError(f'film has no {key} format; it has {", ".join(map(str, self.formats))}')

    def frame(self, n, format=None, scale=1.0):
        """Draw frame `n` into a fresh Canvas."""
        f = self.format(format)
        cv = Canvas(f.width, f.height, self.background, scale=scale, format=f)
        self.draw(n, cv)
        return cv


_counter = itertools.count()


def load_module(path):
    """Import a film file afresh (a new module each call, so edits are seen) and
    return the module: `FILM` and the film's other module-level names (its
    layout tables, say) for tools that check a film. Its directory goes on
    sys.path so it can import its neighbours."""
    path = os.path.abspath(path)
    d = os.path.dirname(path)
    if d not in sys.path:
        sys.path.insert(0, d)
    name = f'_videobuilder_film_{next(_counter)}'
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load(path):
    """The `FILM` of a film file."""
    mod = load_module(path)
    film = getattr(mod, 'FILM', None)
    if not isinstance(film, Film):
        raise TypeError(f'{path} must define FILM = videobuilder.Film(...)')
    return film
