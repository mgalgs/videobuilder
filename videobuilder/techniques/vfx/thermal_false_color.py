"""Thermal false color: the picture's brightness read as heat -- dark areas
go black and violet, mid-tones red and orange, the brightest yellow to
white -- so any shot looks like a thermal camera's view of it."""
import math
from contextlib import contextmanager

from PIL import Image

import videobuilder as vb

from .. import _demo as demo
from ...looks import fx
from ..schema import Technique

# Cold to hot: the stops of the heat palette, (position 0..1, '#rrggbb').
HEAT = ((0.00, '#000004'), (0.18, '#2a0b5c'), (0.36, '#781c6d'), (0.52, '#c2283f'),
        (0.68, '#ed5a1c'), (0.82, '#fba30e'), (0.93, '#f6e05a'), (1.00, '#ffffff'))


def _rgb(c):
    return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)


def heat_ramp(stops=HEAT):
    """The palette as 256 (r, g, b) steps, coldest first, interpolated
    linearly between `stops` ((position, '#rrggbb'), positions rising 0 -> 1)."""
    out = []
    for i in range(256):
        v = i / 255
        for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
            if v <= p1:
                break
        t = 0.0 if p1 == p0 else min(1.0, max(0.0, (v - p0) / (p1 - p0)))
        a, b = _rgb(c0), _rgb(c1)
        out.append(tuple(round(a[k] + (b[k] - a[k]) * t) for k in range(3)))
    return out


def thermal_image(im, amount=1.0, stops=HEAT, gain=1.0, offset=0.0):
    """The PIL image `im` in thermal false colour, as RGB: each pixel's
    brightness looked up on the heat palette. `gain` and `offset` stretch the
    brightness before the lookup (gain 1.3 pushes more of the frame hot,
    offset -0.1 cools it); `amount` blends from the original (0) to the full
    look (1)."""
    ramp = heat_ramp(stops)
    lut = [ramp[max(0, min(255, round((i / 255 * gain + offset) * 255)))] for i in range(256)]
    gray = im.convert('L')
    hot = Image.merge('RGB', [gray.point([c[k] for c in lut]) for k in range(3)])
    if amount >= 1:
        return hot
    return Image.blend(im.convert('RGB'), hot, max(0.0, amount))


def _treat(im, t, age, u, **opts):
    return thermal_image(im, **opts)


FILTER = fx.Filter('thermal-false-color', 'Thermal false color',
                   'brightness mapped to a black-violet-red-yellow-white heat palette', _treat,
                   aliases=('thermal', 'heat map view'))


@contextmanager
def thermal_false_color(cv, amount=1.0, box=None, stops=HEAT, gain=1.0, offset=0.0):
    """Everything drawn inside the block comes out in thermal false colour
    (see `thermal_image`), within `box` (x, y, w, h) if given, else the whole
    frame. Animate `amount` to fade the look in, or `box` to wipe it across:

        with thermal_false_color(cv, box=(0, 0, x, H)):
            draw_the_shot(n, cv)
    """
    with fx.apply(cv, FILTER, 0.0, box=box,
                  opts={'amount': amount, 'stops': stops, 'gain': gain, 'offset': offset}):
        yield cv


# ---- demo ----

def _scene(cv, n):
    """The photo with a warm body drifting across it: a bright glow that
    the heat palette turns white-hot."""
    img = demo.photo()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))
    s = n / demo.FPS
    cx = demo.W * (0.3 + 0.4 * s / demo.SECONDS)
    cy = demo.H * 0.55 + 40 * math.sin(2.1 * s)
    for i in range(28, 0, -1):                     # soft falloff, hottest at the core
        demo.dot(cv, cx, cy, r=36 + 5 * i, color='#ffffff', alpha=0.06)
    demo.dot(cv, cx, cy, r=40, color='#ffffff')


def _legend(cv, x, y, w, h):
    """A thermal camera's cold-to-hot scale bar."""
    ramp = heat_ramp()
    steps = 48
    for i in range(steps):
        r, g, b = ramp[round(255 * (1 - i / (steps - 1)))]
        cv.rect(x, y + h * i / steps, w, h / steps + 1, f'#{r:02x}{g:02x}{b:02x}')
    cv.outline(x, y, w, h, demo.INK, width=2, alpha=0.7)
    f = demo.mono(20)
    vb.text.draw(cv, ['HOT'], f, x - 8, y - 32, demo.INK)
    vb.text.draw(cv, ['COLD'], f, x - 14, y + h + 10, demo.INK)


def draw(n, cv):
    p = vb.ease_in_out_quart(demo.phase(n, 0.4, 2.2))
    x = demo.W * p
    _scene(cv, n)
    if x >= 1:
        with thermal_false_color(cv, box=(0, 0, x, demo.H)):
            _scene(cv, n)
    if 0 < p < 1:
        cv.line(x, 0, x, demo.H, demo.INK, width=3, alpha=0.85)
    _legend(cv, demo.W - 90, demo.H / 2 - 180, 28, 360)


TECHNIQUE = Technique(
    id='thermal-false-color',
    name='Thermal false color',
    family='vfx',
    group='Thermal & sensor',
    aliases=('thermal vision', 'heat map view', 'infrared thermal', 'thermal camera look', 'FLIR look'),
    definition='Each part of the picture is recoloured by how bright it is, from black and violet in the '
               'dark areas through red and orange to yellow-white in the brightest, like a heat camera.',
    phrasings=('make it look like we are seeing it through a thermal camera',
               'turn the shot into an infrared heat view',
               'recolour the footage so bright things glow hot and shadows go cold purple'),
    related=('heatmap-fill', 'heat-haze', 'photographic-negative', 'thin-film-iridescence', 'luma-key',
             'gooch-shading'),
    api=('videobuilder.techniques.vfx.thermal_false_color.thermal_false_color',
         'videobuilder.techniques.vfx.thermal_false_color.thermal_image',
         'videobuilder.techniques.vfx.thermal_false_color.heat_ramp'),
    demo=lambda: demo.film(draw),
)
