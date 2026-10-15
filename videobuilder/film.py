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
from dataclasses import dataclass, replace
from typing import Callable

from . import edits as _edits
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


# The mix's default integrated-loudness target: Audio.loudness when the film has
# music, Film.loudness otherwise (a film with sounds and no music has no Audio to
# carry the override).
DEFAULT_LOUDNESS = -14.0


@dataclass
class Audio:
    """A music track, muxed in by `render`.

    `trim_frames`: frames skipped at the head of the file. None (the default)
    takes the film's `Grid.head_trim`, the trim that lands the track's beats on
    the grid, so the two can't disagree; 0 without a timeline.
    `fade_out_frames`: a linear fade over the k frames before the last one,
    silent from the start of the last frame: gain 1 at frame `frames - 1 - k`
    and 0 at `frames - 1`. Remotion's `interpolate(f, [D - m, D - 1], [1, 0])`
    is `fade_out_frames=m - 1`.
    `loudness`: when the film also has `sounds`, this is the target for the
    whole mix (music plus sounds), not just the music.
    `duck_db`: how far the music drops while any `Sound` plays (e.g. -12); 0
    (the default) means no ducking. The drop ramps over a few frames at each
    edge of a sound's span, as a gain envelope computed from the sounds'
    spans, not a sidechain compressor reacting to the actual signal.
    """
    path: str
    trim_frames: int | None = None
    gain_db: float = 0.0
    fade_out_frames: int = 0
    loudness: float | None = DEFAULT_LOUDNESS
    duck_db: float = 0.0


@dataclass
class Sound:
    """Footage's own audio: a clip's sound, placed on the film's timeline
    alongside the music (see `videobuilder.clip.footage` for building this and
    its matching picture together from a timeline segment).

    `at`: the film frame it starts on. `start`: seconds into the source file.
    `frames`: its length in film frames; clipped to the film's own range.
    `fade_in_frames`/`fade_out_frames`: a short linear ramp at each edge, so a
    cut into or out of the sound doesn't click.
    """
    path: str
    at: int
    start: float
    frames: int
    gain_db: float = 0.0
    fade_in_frames: int = 3
    fade_out_frames: int = 3


@dataclass
class Film:
    """A film: a pure draw function plus its timing and formats.

    `frames` and `fps` may be left out when a `timeline` gives them. The first
    of `formats` is the default; each is a name from `FORMATS` or a `Format`.

    `loudness`: the mix's target when the film has `sounds` and no `audio`,
    so there's still a knob to tell it otherwise (None turns normalisation
    off). Ignored when the film has music: `Audio.loudness` is the target
    for the whole mix then, same as always.
    """
    draw: Callable[[int, Canvas], None]
    fps: int | None = None
    frames: int | None = None
    formats: tuple = ('16x9',)
    background: str | tuple | None = '#000000'
    audio: Audio | None = None
    sounds: tuple = ()
    loudness: float | None = DEFAULT_LOUDNESS
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
        if self.audio is not None and self.audio.trim_frames is None:
            trim = self.timeline.grid.head_trim if self.timeline is not None else 0
            self.audio = replace(self.audio, trim_frames=trim)
        clipped = []
        for s in self.sounds:
            a, z = max(0, s.at), min(self.frames, s.at + s.frames)
            if z <= a:
                continue
            clipped.append(replace(s, at=a, start=s.start + (a - s.at) / self.fps, frames=z - a))
        self.sounds = tuple(clipped)

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


def load_module(path, edits=None):
    """Import a film file afresh (a new module each call, so edits are seen) and
    return the module: `FILM` and the film's other module-level names (its
    layout tables, say) for tools that check a film. Its directory goes on
    sys.path so it can import its neighbours.

    The film's `<stem>.edits.toml` applies to the first Timeline it builds
    (see `videobuilder.edits`); `edits`, an `edits.Edits`, replaces it."""
    path = os.path.abspath(path)
    if edits is None:
        edits = _edits.Edits.read(_edits.path_for(path))
    d = os.path.dirname(path)
    if d not in sys.path:
        sys.path.insert(0, d)
    name = f'_videobuilder_film_{next(_counter)}'
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    # Compiled here, not by exec_module: its bytecode cache trusts mtime and
    # size, so a same-length edit within one second would load the old film.
    with open(path, 'rb') as fh:
        code = compile(fh.read(), path, 'exec')
    with _edits.active(edits):
        exec(code, mod.__dict__)
    if edits is not None and edits.segments and not edits.used:
        raise ValueError(f'{edits.path} has edits, but {path} built no Timeline to apply them to')
    return mod


def forget_neighbours(path):
    """Drop the modules imported from a film's directory, so the next
    `load_module` imports its helpers afresh too."""
    d = os.path.dirname(os.path.abspath(path))
    for name, mod in list(sys.modules.items()):
        f = getattr(mod, '__file__', None)
        if f and os.path.dirname(os.path.abspath(f)) == d:
            del sys.modules[name]


def load(path):
    """The `FILM` of a film file."""
    mod = load_module(path)
    film = getattr(mod, 'FILM', None)
    if not isinstance(film, Film):
        raise TypeError(f'{path} must define FILM = videobuilder.Film(...)')
    return film
