"""Type: named typography styles any video can ask for by name.

A type style is a short, self-contained typography film -- a departures
board, a typewriter, bouncing rubber letters -- drawn from the same few
props every style takes: one to four short `lines`, three colours (`ink`,
`paper`, `accent`) and a `length` in seconds:

    import videobuilder as vb

    TITLE = vb.type.props(lines=['Gate 14', 'Now boarding'], accent='#ffb000')

    def draw(n, cv):
        vb.type.draw(cv, 'split-flap', TITLE, n / FPS)          # the whole frame
        ...

    vb.type.draw(cv, 'rubber', TITLE, t - 2.0, box=(0, 0, cv.width, cv.height * 0.4))  # in a box
    vb.type.draw(cv, 'rack-focus', vb.type.props(TITLE, paper=None), t)   # over the picture drawn so far

    FILM = vb.type.film('typewriter', TITLE, length=18)     # one style as a film of its own

`t` is seconds since the style started: it enters, holds (still moving)
and exits within `length`, drawing nothing but its ground outside it.
`names()` lists the styles; `get(name)` finds one by name, alias or title
("split flap", "departures board"); `sounds(name, props, at)` places its
sound (with `sound=True` and the sound-effects pack installed);
`relay(cv, names, props, t)` plays several in turn; `motion_floor` is the
Looks' check that a hold never freezes, against Type's own FLOOR.

The props, every style, and how to put one over another picture:
skill/make-a-video/reference/type.md.
"""
import logging

from ..looks import motion_floor
from .style import (ACCENT, DEFAULT_LENGTH, INK, MAX_CHARS, MAX_LINES, PAPER, Clock, Props, PropsError, Style,
                    props, with_length)
from .style import _key

__all__ = ['ACCENT', 'Clock', 'DEFAULT_LENGTH', 'FLOOR', 'INK', 'MAX_CHARS', 'MAX_LINES', 'PAPER', 'Props',
           'PropsError', 'Style', 'draw', 'film', 'get', 'motion_floor', 'names', 'props', 'register', 'relay',
           'sounds']

# The Looks' motion floor, at a type style's own bar: a look repaints the whole frame, a type
# style leaves most of it bare paper, so a tenth of the frame's tiles must move through the hold.
FLOOR = 0.10

_REGISTRY = {}
_LOOKUP = {}
_log = logging.getLogger(__name__)


def register(style):
    """Adds `style` to the registry (a video's own style, too). Refuses a
    name or alias already taken."""
    keys = {_key(k) for k in (style.name, style.title, *style.aliases)}
    taken = sorted(k for k in keys if k in _LOOKUP and _LOOKUP[k] is not style)
    if taken:
        raise ValueError(f'type style name already taken: {", ".join(taken)}')
    _REGISTRY[style.name] = style
    for k in keys:
        _LOOKUP[k] = style
    return style


def get(name):
    """The style called `name`: its name, an alias or its title, in any case
    and spacing ("split flap", "Split-Flap board"). KeyError listing every
    name for one that isn't there."""
    style = _LOOKUP.get(_key(name))
    if style is None:
        raise KeyError(f'no type style called {name!r}; styles: {", ".join(names())}')
    return style


def names():
    """Every registered style's name, in registration order."""
    return tuple(_REGISTRY)


def draw(cv, name, p, t, box=None, **opts):
    """Draws the style `name` with props `p` (a Props, a dict or a list of
    lines) at `t` seconds since it started, filling `box` (x, y, w, h; the
    whole canvas by default). With `p.paper` set it paints the box first;
    with `paper=None` it draws only its letters (and their own furniture:
    a board's flaps, a cursor) over what is there."""
    get(name)(cv, props(p), t, box, **opts)


def film(name, p, formats=('9x16', '16x9', '1x1'), fps=30, at=0.0, **kw):
    """The style `name` as a film of its own: `p` (with `kw` over it, so
    `film('rubber', p, length=18)`), from `at` seconds into the film, with
    its sound when `p.sound`. The film runs the style's length plus `at`."""
    from ..film import Film
    style = get(name)
    p = props(p, **kw)
    frames = round((at + p.length) * fps)
    clock = style.clock(p)
    mid = round((at + (clock.hold + clock.exit) / 2) * fps)

    def draw_frame(n, cv):
        style(cv, p, n / fps - at)

    return Film(draw=draw_frame, fps=fps, frames=frames, formats=formats,
                background=p.paper if p.paper is not None else PAPER,
                sounds=sounds(name, p, at=round(at * fps), fps=fps),
                keyframes=((min(frames - 1, mid), 'hold'),))


_noted = set()


def _note_once(key, message):
    if key not in _noted:
        _noted.add(key)
        _log.warning(message)


def _pick(bank, ids, roles):
    """The first of `ids` the pack has, else the first sound of the first of
    `roles` it has, else None."""
    for i in ids:
        if i.split('--')[0] in bank.effects:
            return i
    have = set(bank.roles())
    for role in roles:
        if role in have:
            return bank.find(role)[0].id
    return None


def sounds(name, p, at=0, fps=30):
    """The style's sound effects, as `vb.sfx` sounds placed for a style that
    starts on film frame `at`: () when `p.sound` is off or the style has no
    sound. Without the sound-effects pack the style still draws; this says
    so once (a logged note) and returns ()."""
    from .. import sfx
    style = get(name)
    p = props(p)
    if not p.sound or not style.sound:
        return ()
    try:
        bank = sfx.bank()
    except sfx.SfxUnavailable as e:
        _note_once('pack', f'type: {style.name} plays without its sound: {e}')
        return ()
    picked = {kind: (_pick(bank, ids, roles), gain) for kind, (ids, roles, gain) in style.sound.items()}
    out = []
    for t, kind in style.events(p):
        sid, gain = picked.get(kind, (None, 0))
        if sid is None:
            _note_once((style.name, kind), f'type: {style.name} has no {kind} sound in this pack')
            continue
        out.append(sfx.sound(sid, at=at + round(t * fps), fps=fps, gain_db=gain))
    return tuple(out)


def relay(cv, names_, p, t, each=None, box=None, opts=None):
    """Plays each of `names_` in turn with props `p`, `each` seconds apiece
    (default p.length), every one running its own enter, hold and exit --
    "show me a few type styles". Returns the name on screen."""
    p = props(p)
    names_ = list(names_)
    each = each or p.length
    q = with_length(p, each)
    i = int(max(0.0, t) // each)
    current = names_[i % len(names_)]
    draw(cv, current, q, t - i * each, box, **(opts or {}).get(current, {}))
    return current


def relay_sounds(names_, p, each=None, at=0, fps=30):
    """`sounds` for every style of a `relay`, each at its turn."""
    p = props(p)
    each = each or p.length
    q = with_length(p, each)
    return tuple(s for i, name in enumerate(names_) for s in sounds(name, q, at=at + round(i * each * fps), fps=fps))


from . import cloud, editorial, rackfocus, rubber, splitflap, typewriter  # noqa: E402

for _style in (splitflap.STYLE, typewriter.STYLE, typewriter.TERMINAL, rubber.STYLE, rackfocus.STYLE, cloud.STYLE,
               editorial.STYLE):
    register(_style)
del _style
