"""Infrared false color: the colour-infrared film look. Real colour-infrared
film records near-infrared as red, red as green and green as blue; leaves
reflect near-infrared strongly, so foliage comes out red to magenta while
blue sky and water, which reflect almost none, go dark. A normal picture
has no infrared channel, so `infrared_false_color` estimates one from the
visible channels (green high, blue low reads as foliage) and makes the same
shift with one Pillow channel matrix.

    with infrared(cv, amount=p):        # everything drawn inside is remapped
        draw_the_landscape(n, cv)

It runs through the filter-look plumbing (`looks.fx.apply`), so it treats
whatever is on the canvas -- a photo, footage, vector shapes -- at the
canvas's real resolution, or only the pixels in `box`.
"""
import math

from PIL import Image

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ...looks import fx
from ...looks import kit as lk

# out = matrix . (R, G, B, 1): the estimated near-infrared goes to red, red to green, green to blue
NIR = (0.30, 1.45, -0.80, 0)      # bright where green beats blue: foliage glows, sky and water fall away
MATRIX = (*NIR,
          0.92, 0.0, 0.0, 0,
          0.0, 0.80, 0.10, 0)


def infrared_false_color(im, amount=1.0):
    """`im` (a PIL RGB image) remapped to colour-infrared false colour:
    foliage red to magenta, sky and water dark. `amount` 0 -> 1 blends from
    the original to the full remap."""
    amount = vb.clamp01(amount)
    if amount <= 0:
        return im
    out = im.convert('RGB', MATRIX)
    return out if amount >= 1 else Image.blend(im, out, amount)


def _treat(im, t, age, u, amount=1.0):
    return infrared_false_color(im, amount)


FILTER = fx.Filter('infrared-false-color', 'Infrared false color', 'foliage red, sky dark', _treat,
                   aliases=('color infrared', 'ir false color'))


def infrared(cv, amount=1.0, box=None):
    """A context manager: everything on `cv` when the block ends (drawn
    inside it or before) is remapped by `infrared_false_color` at `amount`,
    every pixel or only those in `box`, (x, y, w, h) in frame px. Draw copy
    that must keep its colours after the block."""
    return fx.apply(cv, FILTER, 0.0, box=box, opts={'amount': amount})


# ---- the demo: a green landscape a sensor line sweeps across ----

def _ridge(y, amp, waves, phase, step=40):
    pts = [(x, y + amp * math.sin(x / demo.W * waves * math.pi + phase)) for x in range(0, demo.W + step, step)]
    return [(0, demo.H), *pts, (demo.W, demo.H)]


def _tree(cv, x, base, h, colour):
    w = h * 0.42
    cv.rect(x - h * 0.04, base - h * 0.2, h * 0.08, h * 0.22, '#3d2b1f')
    for i in range(3):
        top = base - h + i * h * 0.22
        lk.fill(cv, [(x, top), (x - w * (0.6 + 0.2 * i), top + h * 0.42), (x + w * (0.6 + 0.2 * i), top + h * 0.42)],
                colour)


def landscape(cv, t):
    """A daylight scene in plain visible colours: blue sky, sun, clouds,
    green hills, a meadow, trees and a lake."""
    W, H = demo.W, demo.H
    top, low = (52, 112, 205), (122, 176, 236)
    for i in range(24):
        k = i / 23
        cv.rect(0, i * H * 0.6 / 24, W, H * 0.6 / 24 + 1, tuple(round(a + (b - a) * k) for a, b in zip(top, low)))
    demo.dot(cv, W * 0.78, H * 0.2, r=H * 0.065, color='#fff6dc')
    for cx, cy, s in ((0.18, 0.16, 1.0), (0.52, 0.11, 0.8), (0.95, 0.3, 0.9)):
        s *= H / 1080
        x = (cx * W + 20 * t) % (W + 150) - 75
        for dx, dy, r in ((0, 0, 46), (52, -18, 56), (110, 0, 44), (55, 14, 50)):
            demo.dot(cv, x + dx * s, cy * H + dy * s, r=r * s, color='#f4f7fb')
    lk.fill(cv, _ridge(H * 0.5, H * 0.04, 3, 0.6), '#5f8f6a')        # far hills, hazy green
    lk.fill(cv, _ridge(H * 0.6, H * 0.03, 2, 2.0), '#4f9a3c')        # near hills
    lk.fill(cv, _ridge(H * 0.74, H * 0.015, 4, 1.1), '#79c043')       # bright meadow
    cv.ctx.save()                                               # the lake
    cv.ctx.translate(W * 0.46, H * 0.87)
    cv.ctx.scale(1.0, 0.22)
    cv.ctx.arc(0, 0, W * 0.17, 0, 2 * math.pi)
    cv.ctx.restore()
    cv.ctx.set_source_rgb(*(c / 255 for c in (46, 102, 178)))
    cv.ctx.fill()
    for x, base, h, c in ((0.07, 0.70, 0.28, '#2f6b2a'), (0.17, 0.67, 0.2, '#37782f'), (0.70, 0.69, 0.24, '#2f6b2a'),
                          (0.82, 0.74, 0.32, '#2a6226'), (0.93, 0.68, 0.22, '#37782f')):
        _tree(cv, x * W, base * H, h * H, c)


def draw(n, cv):
    t = n / demo.FPS
    p = vb.ease_in_out_quart(demo.phase(n, 0.5, 2.3))
    edge = demo.W * p
    landscape(cv, t)
    if edge > 1:
        with infrared(cv, box=(0, 0, edge, demo.H)):
            pass
    if 0 < p < 1:
        cv.line(edge, 0, edge, demo.H, '#ffffff', width=8, alpha=0.18)
        cv.line(edge, 0, edge, demo.H, '#ffffff', width=2, alpha=0.9)
    f = demo.mono(18, 700)
    if edge > 150:
        vb.text.draw(cv, ['INFRARED'], f, 24, 20, demo.INK)
    if edge < demo.W - 150:
        w, _ = vb.text.block_size(['VISIBLE'], f)
        vb.text.draw(cv, ['VISIBLE'], f, demo.W - 24 - w, 20, '#0d1b2a')


TECHNIQUE = Technique(
    id='infrared-false-color',
    name='Infrared false color',
    family='vfx',
    group='Thermal & sensor',
    aliases=('IR false color', 'color infrared', 'channel remap infrared', 'CIR'),
    definition='A colour remap that imitates infrared film, turning leaves and grass red or magenta '
               'while blue sky and water sink to near black.',
    phrasings=('make it look like an infrared photo with red trees',
               'shift the colours so the greenery goes pink and the sky goes dark',
               'give the landscape that false-colour infrared camera look'),
    related=('rgb-split', 'rgb-channel-split', 'channel-shuffle', 'thin-film-iridescence',
             'photographic-negative', 'solarization'),
    api=('videobuilder.techniques.vfx.infrared_false_color.infrared_false_color',
         'videobuilder.techniques.vfx.infrared_false_color.infrared'),
    demo=lambda: demo.film(draw),
)
