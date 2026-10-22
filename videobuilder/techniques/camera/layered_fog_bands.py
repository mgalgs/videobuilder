"""Layered fog bands: soft horizontal strips of mist sit at several depths in
a scene, between its far and near layers, and each drifts sideways at its
own speed -- slow and pale far off, faster and denser up close -- so the
scene reads as deep air rather than a flat backdrop."""
from dataclasses import dataclass
from functools import lru_cache

import cairo

from videobuilder import parallax, paths

from .. import _demo as demo
from ..schema import Technique


@dataclass(frozen=True)
class FogBand:
    """One strip of fog. `y` is its centre line and `thickness` its full
    height, in frame px; its top and bottom edges roll by up to `wave` px.
    `depth` scales the camera's pan as in `parallax.Layer` (under 1 is far
    and slow); `wind` adds its own drift in px per second on top. `opacity`
    is its density at the thickest point, fading to nothing at both edges.
    `width` is one seamless tile; `seed` shapes its edges."""
    y: float
    thickness: float
    depth: float = 0.5
    wind: float = 20.0
    opacity: float = 0.55
    color: str = '#dfe3ea'
    wave: float = 26.0
    width: float = 960.0
    seed: int = 1


def _rgb(color):
    return tuple(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))


@lru_cache(maxsize=32)
def _edges(band):
    """Two passes of `(top, bottom)` edge tiles for `band`, each a seamless
    ridge: painting both with different edges makes the strip billow rather
    than read as a bar. Cached per band."""
    return [(parallax.ridge(band.width, band.wave, seed=band.seed * 7 + k, bumps=(1, 2, 4)),
             parallax.ridge(band.width, band.wave, seed=band.seed * 13 + k, bumps=(1, 3)))
            for k in range(2)]


def fog_band(cv, band, t, camera_x=0.0):
    """Draw one `FogBand` across the whole frame at time `t` seconds with the
    camera panned `camera_x` px: it sits `camera_x * depth + wind * t` px
    along, its edge tiles repeating seamlessly. Each pass is one path across
    the frame, filled with a vertical gradient clear at both edges and
    densest just above the middle."""
    half = band.thickness / 2
    y0, y1 = band.y - half - band.wave, band.y + half + band.wave
    x0 = parallax.offset(parallax.Layer(1.0, band.width, None), camera_x * band.depth + band.wind * t)
    tiles = int((cv.width - x0) // band.width) + 1
    r, g, b = _rgb(band.color)
    grad = cairo.LinearGradient(0, y0, 0, y1)
    for stop, a in ((0.0, 0.0), (0.3, 0.75), (0.5, 1.0), (0.75, 0.5), (1.0, 0.0)):
        grad.add_color_stop_rgba(stop, r, g, b, a * band.opacity * 0.62)
    c = cv.ctx
    for top, bottom in _edges(band):
        span = lambda edge: [(x0 + i * band.width + px, py) for i in range(tiles) for px, py in edge]  # noqa: E731
        pts = [(x, y0 + py) for x, py in span(top)]
        pts += [(x, y1 - py) for x, py in reversed(span(bottom))]
        c.new_path()
        c.move_to(*pts[0])
        for p in pts[1:]:
            c.line_to(*p)
        c.close_path()
        c.set_source(grad)
        c.fill()


def layered_fog(cv, layers, t, camera_x=0.0):
    """Draw a scene interleaved with fog: `layers` is far-first, each either
    a `FogBand` or a `parallax.Layer` (the scenery between the bands). Every
    item pans by its own depth and the bands also drift on their own wind,
    so mist slips between hills, buildings or titles at different speeds."""
    for item in layers:
        if isinstance(item, FogBand):
            fog_band(cv, item, t, camera_x)
        else:
            parallax.draw(cv, [item], camera_x)


# ---- the demo: four ridges at dusk, a fog band settled in each valley ----

TILE = 960
RIDGES = [(parallax.ridge(TILE, h, seed=s), top, color, depth)
          for h, s, top, color, depth in ((90, 4, 200, '#4b5568', 0.15), (110, 9, 265, '#353d4f', 0.35),
                                          (120, 2, 330, '#252a37', 0.65), (130, 6, 400, '#16181f', 1.0))]


def _ridge_layer(pts, top, color, depth):
    shape = pts + [(TILE + 1, pts[-1][1]), (TILE + 1, demo.H - top + 10), (0, demo.H - top + 10)]  # 1 px overlap: no seam

    def draw(cv, x):
        paths.draw(cv, [(x + px, top + py) for px, py in shape], color, fill=True)
    return parallax.Layer(depth, TILE, draw)


def _sky(cv):
    c = cv.ctx
    grad = cairo.LinearGradient(0, 0, 0, demo.H)
    for stop, color in ((0.0, '#1b2233'), (0.55, '#5a6278'), (1.0, '#c9b9a8')):
        grad.add_color_stop_rgb(stop, *_rgb(color))
    c.rectangle(0, 0, demo.W, demo.H)
    c.set_source(grad)
    c.fill()
    demo.dot(cv, demo.W * 0.72, 150, 44, color='#f1e4cf', alpha=0.9)


SCENE = []
for i, (pts, top, color, depth) in enumerate(RIDGES):
    SCENE.append(_ridge_layer(pts, top, color, depth))
    SCENE.append(FogBand(y=top + 75, thickness=40 + 14 * i, depth=depth * 1.1,
                         wind=10 + 32 * i, opacity=0.4 + 0.12 * i, wave=14 + 5 * i, seed=i + 1))


def draw(n, cv):
    t = n / demo.FPS
    _sky(cv)
    layered_fog(cv, SCENE, t, camera_x=90 * t)  # a slow, steady pan


TECHNIQUE = Technique(
    id='layered-fog-bands',
    name='Layered fog bands',
    family='camera',
    group='Depth',
    aliases=('atmospheric fog layers', 'mist layers', 'depth fog', 'rolling fog bands'),
    definition='Soft horizontal strips of mist sit between the near and far layers of a scene, each sliding '
               'sideways at its own speed, so the picture gains a sense of deep, hazy air.',
    phrasings=('put drifting bands of mist between the hills so it feels deep',
               'misty valley layers that slide past at different speeds',
               'add some low fog rolling between the background layers'),
    related=('parallax-slide', 'parallax-letter-layers', 'scroll-parallax-layers', 'smoke-dissolve',
             'heat-haze', 'pointer-parallax-layers'),
    api=('videobuilder.techniques.camera.layered_fog_bands.layered_fog',
         'videobuilder.techniques.camera.layered_fog_bands.fog_band',
         'videobuilder.techniques.camera.layered_fog_bands.FogBand',
         'videobuilder.parallax.draw'),
    demo=lambda: demo.film(draw),
)
