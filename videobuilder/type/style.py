"""The Type contract: the props every style takes, the clock that splits a
style's run into enter, hold and exit, and the Style type itself."""
import math
import numbers
from dataclasses import dataclass, replace

from ..canvas import rgba
from ..layout import Box
from ..looks.look import _key

MAX_LINES = 4
MAX_CHARS = 24          # a line, in characters: a board, a stack or a title, not a paragraph
MIN_LENGTH, MAX_LENGTH = 2.0, 30.0
DEFAULT_LENGTH = 6.0

INK = '#f4f1ea'
PAPER = '#15161b'
ACCENT = '#ef5b4c'


class PropsError(ValueError):
    """Bad props for a type style: the message says which and why."""


@dataclass(frozen=True)
class Props:
    """What every style takes, and nothing else.

    - `lines`: 1 to 4 short lines (at most MAX_CHARS each), laid out as given:
      a style never rewraps them, it sizes them to the frame.
    - `ink`, `paper`, `accent`: the letters, the ground and the one strong
      colour. `paper=None` draws no ground: the style goes over whatever
      picture is already on the canvas.
    - `length`: seconds the style runs, enter to exit (6 s inside a film;
      up to 18 s and more as a film of its own).
    - `sound`: whether `type.sounds` places the style's sound (off by default).
    - `texture`: the surface over the ground -- the typewriter's paper grain,
      the terminal's scanlines, the editorial page's grain (on by default).
      Off keeps the paper colour and every letter.
    - `font`: a font family for the letters, or None for the style's own
      generic family (sans-serif, monospace or serif, as fontconfig has it)."""
    lines: tuple
    ink: object = INK
    paper: object = PAPER
    accent: object = ACCENT
    length: float = DEFAULT_LENGTH
    sound: bool = False
    texture: bool = True
    font: str | None = None

    @property
    def text(self):
        return '\n'.join(self.lines)


_FIELDS = ('lines', 'ink', 'paper', 'accent', 'length', 'sound', 'texture', 'font')


def _colour(name, value, allow_none=False):
    if value is None and allow_none:
        return None
    try:
        rgba(value)
    except Exception:  # noqa: BLE001 -- rgba raises whatever its parser does; one message for all of it
        none = ' (or None for no ground)' if allow_none else ''
        raise PropsError(f'type props: {name} must be a colour like "#ef5b4c" or (239, 91, 76){none}, '
                         f'not {value!r}') from None
    return value


def props(value=None, **kw):
    """Props from a Props, a dict, or keywords (`type.props(lines=[...],
    accent='#ff0')`); keywords override `value`'s. A string for `lines` is
    split at its newlines. Raises PropsError naming the first bad prop."""
    if isinstance(value, Props):
        base = {f: getattr(value, f) for f in _FIELDS}
    elif value is None:
        base = {}
    elif isinstance(value, dict):
        base = dict(value)
    elif isinstance(value, (str, list, tuple)):
        base = {'lines': value}
    else:
        raise PropsError(f'type props: expected a Props, a dict or lines, not {type(value).__name__}')
    base.update(kw)
    unknown = sorted(set(base) - set(_FIELDS))
    if unknown:
        raise PropsError(f'type props: unknown prop{"s" if len(unknown) > 1 else ""} {", ".join(unknown)}; '
                         f'a style takes {", ".join(_FIELDS)}')
    if 'lines' not in base or base['lines'] is None:
        raise PropsError('type props: lines is required: 1 to 4 short lines of text')
    lines = base['lines']
    if isinstance(lines, str):
        lines = lines.split('\n')
    if not isinstance(lines, (list, tuple)) or not all(isinstance(ln, str) for ln in lines):
        raise PropsError('type props: lines must be a string or a list of strings')
    lines = tuple(' '.join(ln.split()) for ln in lines)
    if not 1 <= len(lines) <= MAX_LINES:
        raise PropsError(f'type props: lines must be 1 to {MAX_LINES} short lines, not {len(lines)}')
    for i, ln in enumerate(lines):
        if not ln:
            raise PropsError(f'type props: line {i + 1} is empty')
        if len(ln) > MAX_CHARS:
            raise PropsError(f'type props: line {i + 1} is {len(ln)} characters; keep each line to {MAX_CHARS} '
                             f'or split it ({ln!r})')
    out = {'lines': lines}
    for name in ('ink', 'accent'):
        out[name] = _colour(name, base.get(name, getattr(Props, name)))
    out['paper'] = _colour('paper', base.get('paper', PAPER), allow_none=True)
    length = base.get('length', DEFAULT_LENGTH)
    if isinstance(length, bool) or not isinstance(length, numbers.Real) or not math.isfinite(length) or \
            not MIN_LENGTH <= length <= MAX_LENGTH:
        raise PropsError(f'type props: length is seconds, {MIN_LENGTH:g} to {MAX_LENGTH:g}, not {length!r}')
    out['length'] = float(length)
    sound = base.get('sound', False)
    if not isinstance(sound, bool):
        raise PropsError(f'type props: sound is True or False, not {sound!r}')
    out['sound'] = sound
    texture = base.get('texture', True)
    if not isinstance(texture, bool):
        raise PropsError(f'type props: texture is True or False, not {texture!r}')
    out['texture'] = texture
    font = base.get('font')
    if font is not None and (not isinstance(font, str) or not font.strip()):
        raise PropsError(f'type props: font is a font family name, or None for the style\'s own, not {font!r}')
    out['font'] = font
    return Props(**out)


class Clock:
    """A style's run of `length` seconds in three parts: the enter (0 to
    `hold` s), the hold (`hold` to `exit` s) and the exit (`exit` to `length`). The enter takes
    about two fifths of the run, the exit about a seventh, each within
    bounds, so a 6 s run holds for 2.7 s and an 18 s one for 12.6 s."""

    def __init__(self, length, enter=None, exit=None):
        self.length = length
        self.hold = enter if enter is not None else min(4.0, max(1.2, 0.4 * length))
        out = exit if exit is not None else min(1.4, max(0.5, 0.15 * length))
        self.exit = length - out

    def entering(self, t):
        """0 -> 1 through the enter."""
        return min(1.0, max(0.0, t / self.hold))

    def leaving(self, t):
        """0 -> 1 through the exit."""
        return min(1.0, max(0.0, (t - self.exit) / (self.length - self.exit)))

    def held(self, t):
        """Seconds into the hold (negative before it)."""
        return t - self.hold


class Style:
    """A named type style: `draw(cv, props, t, box, clock, **opts)` draws
    `props.lines` in this style inside `box` (frame px) at `t` seconds since
    the style started; `type.draw` fills the ground and clips to the box
    first. `title` is the human name, `line` says what moves, `aliases` are
    other names `type.get` accepts.

    `events(props, clock)` lists the style's sound events as (seconds,
    kind) -- a flap, a key, a pop -- with `sound` saying, per kind, the
    pack's sounds to try in order, the roles to fall back on, and the gain:
    {kind: (ids, roles, gain_db)}. `clock(props)` gives the style's own
    Clock, when its enter depends on the copy (a typewriter's keystrokes)."""

    def __init__(self, name, title, line, draw, aliases=(), events=None, sound=None, clock=None, family='sans-serif'):
        if _key(name) != name:
            raise ValueError(f'type style name {name!r} must be lowercase words joined by hyphens')
        self.name, self.title, self.line, self._draw = name, title, line, draw
        self.aliases = tuple(aliases)
        self._events = events
        self.sound = dict(sound or {})
        self._clock = clock
        self.family = family

    def clock(self, p):
        return self._clock(p) if self._clock else Clock(p.length)

    def events(self, p):
        return list(self._events(p, self.clock(p))) if self._events else []

    def font_family(self, p):
        return p.font or self.family

    def __call__(self, cv, p, t, box=None, **opts):
        box = Box.of(cv) if box is None else Box(*box)
        clock = self.clock(p)
        if p.paper is not None:
            cv.rect(*box, p.paper)
        if t < 0 or t >= p.length:
            return
        with cv.clip(*box):
            self._draw(cv, p, t, box, clock, **opts)

    draw = __call__

    def __repr__(self):
        return f'<type style {self.name}: {self.title}>'


def with_length(p, length):
    """`p` at another length."""
    return replace(p, length=float(length))
