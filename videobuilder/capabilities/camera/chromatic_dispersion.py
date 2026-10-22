"""Chromatic dispersion: the picture spreads into a rainbow at its edges, as
if seen through a prism or a cheap lens -- each band of the spectrum is
magnified a little more than the last about the centre, so the middle stays
sharp and the fringes widen towards the borders of the frame."""
import colorsys
import math

import cairo

from .. import _demo as demo
from ..schema import Capability


def spectrum(bands):
    """`bands` rainbow tints from red to violet, scaled so each of red, green
    and blue sums to exactly 1 across them: added back together where they
    overlap, they give the untinted picture."""
    hues = [colorsys.hsv_to_rgb(0.78 * i / max(1, bands - 1), 1.0, 1.0) for i in range(bands)]
    totals = [sum(h[ch] for h in hues) or 1.0 for ch in range(3)]
    return [tuple(h[ch] / totals[ch] for ch in range(3)) for h in hues]


def chromatic_dispersion(cv, draw, amount, cx=None, cy=None, bands=10):
    """Draw `draw(cv)` dispersed by `amount`: it is split into `bands` tints of
    the spectrum (see `spectrum`), each magnified about (`cx`, `cy`, the frame
    centre by default) by up to `1 + amount` -- red least, violet most -- and
    added back together. At the centre the picture is untouched; out towards
    the edges every contrasty edge fans into a rainbow fringe. `amount` around
    0.01-0.04 reads as lens fringing, 0.08 and up as a prism. With `amount` 0
    it is the plain picture. `draw` should paint the whole frame opaquely."""
    cx = cv.width / 2 if cx is None else cx
    cy = cv.height / 2 if cy is None else cy
    c = cv.ctx
    c.push_group()
    draw(cv)
    picture = c.pop_group()
    picture.set_extend(cairo.EXTEND_PAD)
    tints = spectrum(bands)
    c.push_group()
    c.set_source_rgb(0, 0, 0)
    c.paint()
    for i, rgb in enumerate(tints):
        s = 1 + amount * i / max(1, bands - 1)
        c.push_group()
        c.save()
        c.translate(cx, cy)
        c.scale(s, s)
        c.translate(-cx, -cy)
        c.set_source(picture)
        c.paint()
        c.restore()
        c.set_operator(cairo.OPERATOR_MULTIPLY)
        c.set_source_rgb(*rgb)
        c.paint()
        c.set_operator(cairo.OPERATOR_OVER)
        band = c.pop_group()
        c.set_operator(cairo.OPERATOR_ADD)
        c.set_source(band)
        c.paint()
        c.set_operator(cairo.OPERATOR_OVER)
    c.pop_group_to_source()
    c.paint()


def _scene(cv):
    """White rings spread out to the frame's edges on the dark
    ground, with a word in the middle: hard edges everywhere for the fringes."""
    cv.fill(demo.BG)
    for gx in range(7):
        for gy in range(4):
            x = demo.W * (gx + 0.5) / 7
            y = demo.H * (gy + 0.5) / 4
            if abs(x - demo.W / 2) < demo.W * 0.2 and abs(y - demo.H / 2) < demo.H * 0.2:
                continue
            cv.arc(x, y, 46, 0, 2 * math.pi, demo.INK, width=12)
    demo.word(cv, 'PRISM', demo.W / 2, demo.H / 2, size=150)


def _draw(n, cv):
    p = demo.phase(n, 0.3, 1.6)
    amount = 0.075 * (p * p * (3 - 2 * p)) * (1 + 0.08 * math.sin(n / demo.FPS * 5))
    chromatic_dispersion(cv, _scene, amount)


CAPABILITY = Capability(
    id='chromatic-dispersion',
    name='Chromatic dispersion',
    family='camera',
    group='Lighting & surface',
    aliases=('lateral chromatic aberration', 'prism effect', 'colour fringing', 'spectral dispersion',
             'lens dispersion'),
    definition='The image breaks into rainbow fringes that are barely there at the centre and grow wider '
               'towards the edges of the frame, like light bent through a prism or a soft lens.',
    phrasings=('make the edges of the shot split into rainbows like a prism',
               'add lens colour fringing that gets stronger towards the corners',
               'give it that dispersed, spectral glass look around the edges'),
    related=('rgb-split', 'rgb-channel-split', 'palette-shift-transition', 'film-dissolve', 'flash-cut',
             'hue-cycle-fill'),
    api=('videobuilder.capabilities.camera.chromatic_dispersion.chromatic_dispersion',
         'videobuilder.capabilities.camera.chromatic_dispersion.spectrum'),
    demo=lambda: demo.film(_draw),
)
