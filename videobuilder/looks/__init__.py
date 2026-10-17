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

The contract, how to adopt a look and how to write a new one:
skill/make-a-video/reference/looks.md.
"""
from .look import Look, _key
from .scene import ROLES, Region, Scene, lighthouse

__all__ = ['FLOOR', 'Look', 'ROLES', 'Region', 'Scene', 'get', 'lighthouse', 'motion_floor', 'names', 'paint',
           'register', 'relay']


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
del _m
