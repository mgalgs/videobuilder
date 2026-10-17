"""Looks: named art styles any video can be painted in.

A look repaints a *scene description* (looks.Scene: a few polygons with
roles -- sky, water, land, building, figure, light -- plus the sun, a
beacon and stars) in its own style, with its own signature motion:

    from videobuilder import looks

    def draw(n, cv):
        scene = my_scene(cv.width, cv.height, n / FPS)    # this video's shapes, as a Scene
        looks.paint(cv, 'pop-art', scene, n / FPS)         # or looks.get('pop-art')(cv, scene, t)
        ...  # the video's own copy, drawn on top

`looks.names()` lists every look; `looks.get(name)` finds one by name,
alias or title ("pop art", "Pop-art halftone"); `looks.relay` cycles through
several with a wipe ("try a few looks"); `looks.lighthouse(w, h, t)` is a
ready-made scene. `looks.motion_floor` fails a look that barely moves.

A *filter* look restyles pixels instead -- a photo, a screen capture,
footage -- whatever the film draws inside the block:

    with looks.filter(cv, 'pop-art', t):
        draw_the_video_as_usual(n, cv)

Scene looks and filter looks share names where the style carries over, and
the call decides which you get: `paint`/`get`/`names` are the scene looks
(for a video that describes a Scene), `filter`/`get_filter`/`filters` the
filter looks (for anything else). Every name, alias and title of a scene
look also finds its filter of the same name.

The contract, how to adopt a look and how to write a new one:
skill/make-a-video/reference/looks.md.
"""
from .fx import Filter, apply as _apply_filter
from .look import Look, _key
from .scene import ROLES, Region, Scene, lighthouse

__all__ = ['FLOOR', 'Filter', 'Look', 'ROLES', 'Region', 'Scene', 'filter', 'filters', 'get', 'get_filter',
           'lighthouse', 'motion_floor', 'names', 'paint', 'register', 'register_filter', 'relay']


_REGISTRY = {}
_LOOKUP = {}


def register(look):
    """Adds `look` to the registry (a video's own look, too). Refuses a name
    or alias already taken."""
    keys = {_key(k) for k in (look.name, look.title, *look.aliases)}
    taken = sorted(k for k in keys if k in _LOOKUP and _LOOKUP[k] is not look)
    if taken:
        raise ValueError(f'look name already taken: {", ".join(taken)}')
    _REGISTRY[look.name] = look
    for k in keys:
        _LOOKUP[k] = look
    return look


def get(name):
    """The look called `name`: its name, an alias or its title, in any case
    and spacing ("pop art", "Pop-Art", "pop-art halftone"). KeyError listing
    every name for one that isn't there."""
    look = _LOOKUP.get(_key(name))
    if look is None:
        raise KeyError(f'no look called {name!r}; looks: {", ".join(names())}')
    return look


def names():
    """Every registered look's name, in registration order."""
    return tuple(_REGISTRY)


def paint(cv, name, scene, t, age=None, **opts):
    """`get(name)(cv, scene, t, age, **opts)`."""
    get(name)(cv, scene, t, age, **opts)


def relay(cv, scene, t, looks, hold=2.0, wipe=0.5, edge=(255, 248, 220, 0.9), start=0.0, opts=None):
    """Paints `scene` in each of `looks` (names) in turn, `hold` seconds
    each from `start`, every one wiping in over the last from the left over
    `wipe` seconds behind a bright edge -- "try a few looks". `opts`: extras
    per look, {name: {...}}. Returns the name on screen."""
    opts = opts or {}
    from ..ease import ease_out_expo
    looks = list(looks)
    t_in = max(0.0, t - start)
    i = int(t_in / hold + 1e-9)
    age = t_in - i * hold
    current = looks[i % len(looks)]
    if i == 0 or age >= wipe:
        paint(cv, current, scene, t, age, **opts.get(current, {}))
        return current
    before = looks[(i - 1) % len(looks)]
    paint(cv, before, scene, t, hold + age, **opts.get(before, {}))
    p = ease_out_expo(age / wipe)
    with cv.clip(0, 0, scene.w * p, scene.h):
        paint(cv, current, scene, t, age, **opts.get(current, {}))
    cv.rect(scene.w * p - 6 * scene.u, 0, 12 * scene.u, scene.h, edge)
    return current


# ---- filter looks: the same styles laid over pixels ----

_FILTERS = {}
_FILTER_LOOKUP = {}


def register_filter(flt):
    """Adds the filter look `flt` to the registry. It answers to its own
    name, title and aliases and, when a scene look of the same name exists,
    to every name, alias and title of that look too, so "comic" finds the
    pop-art filter as it finds the pop-art look. Refuses a key another
    filter already holds."""
    keys = {_key(k) for k in (flt.name, flt.title, *flt.aliases)}
    twin = _REGISTRY.get(flt.name)
    if twin is not None:
        keys |= {_key(k) for k in (twin.name, twin.title, *twin.aliases)}
    taken = sorted(k for k in keys if k in _FILTER_LOOKUP and _FILTER_LOOKUP[k] is not flt)
    if taken:
        raise ValueError(f'filter name already taken: {", ".join(taken)}')
    _FILTERS[flt.name] = flt
    for k in keys:
        _FILTER_LOOKUP[k] = flt
    return flt


def get_filter(name):
    """The filter look called `name` (its name, an alias or its title, or
    any name of the scene look it shares a name with). KeyError for one
    that isn't there, saying so when `name` is a scene look with no filter."""
    flt = _FILTER_LOOKUP.get(_key(name))
    if flt is None:
        scene_only = _LOOKUP.get(_key(name))
        hint = (f'{scene_only.name!r} is a scene look only: describe the picture as a looks.Scene and '
                f'looks.paint it; ' if scene_only else '')
        raise KeyError(f'no filter look called {name!r}; {hint}filters: {", ".join(filters())}')
    return flt


def filters():
    """Every registered filter look's name, in registration order."""
    return tuple(_FILTERS)


def filter(cv, name, t, age=None, box=None, **opts):  # noqa: A001 -- looks.filter reads as what it does
    """A context manager: everything drawn on `cv` inside the block -- and
    whatever was on it already -- is treated by the filter look `name` when
    the block ends, every pixel (or only those in `box`, (x, y, w, h) in
    frame px), and composited back. Draw copy that must stay readable after
    the block. The body draws on `cv` as usual (it is also what `as`
    yields); it is drawn into an offscreen surface, so the treatment works
    at the canvas's real resolution, preview scale included.

    `t`: film time in seconds, which the filter's own motion runs on;
    `age`: seconds since it came on screen (defaults to `t`); `opts`: the
    filter's extras (pixel's `block=`, pointillism's `pitch=`)."""
    return _apply_filter(cv, get_filter(name), t, age, box, opts)


# ---- the motion floor: a look that barely moves reads as a still ----
FLOOR = 0.20   # something must visibly move in at least a fifth of the frame's tiles


def motion_floor(film, start, end, fmt=None, samples=3, gap=10, scale=0.25, tile=60, threshold=12):
    """How much of the frame moves while a look holds, frames `start` to
    `end` of `film`: the share of tiles (`tile` px square at film size) in
    which any pixel changes by more than a faint flicker between frames
    `gap` apart, the lowest of `samples` moments through the span. Compare
    it with FLOOR. Counting tiles rather than pixels is fair to line art: a
    thin line moving across the whole sea counts, one twitching corner on a
    still painting does not."""
    from PIL import Image, ImageChops
    fmt = fmt or film.formats[0]

    def grab(n):
        cv = film.frame(n, fmt, scale=scale)
        cv.surface.flush()
        w, h = cv.surface.get_width(), cv.surface.get_height()
        return Image.frombuffer('RGBA', (w, h), bytes(cv.surface.get_data()), 'raw', 'BGRA',
                                cv.surface.get_stride(), 1).convert('RGB')

    scores = []
    for i in range(samples):
        f0 = start + (end - start - gap) * i // max(1, samples - 1)
        r, g, b = ImageChops.difference(grab(f0), grab(f0 + gap)).split()
        moved = ImageChops.lighter(ImageChops.lighter(r, g), b).point(lambda v: 255 if v > threshold else 0)
        k = max(1, int(tile * scale))
        tw, th = moved.width // k, moved.height // k
        hits = sum(1 for ty in range(th) for tx in range(tw)
                   if moved.crop((tx * k, ty * k, tx * k + k, ty * k + k)).getbbox())
        scores.append(hits / max(1, tw * th))
    return min(scores)


from . import blueprint, bauhaus, melt, pixel, pointillism, popart, swirl, woodblock  # noqa: E402

for _m in (swirl, pointillism, woodblock, melt, bauhaus, popart, pixel, blueprint):
    register(_m.LOOK)

from .fx import blueprint as _fx_blueprint, pixel as _fx_pixel, pointillism as _fx_pointillism  # noqa: E402
from .fx import popart as _fx_popart, woodblock as _fx_woodblock  # noqa: E402

for _m in (_fx_popart, _fx_pixel, _fx_woodblock, _fx_blueprint, _fx_pointillism):
    register_filter(_m.FILTER)
del _m
