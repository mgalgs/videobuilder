"""Duotone: the picture's colour is thrown away and its brightness re-inked in
two colours -- one for the shadows, one for the highlights, a blend of the two
between -- like a two-ink print. Built on the filter-look pipeline
(`looks.fx.apply`), so it treats whatever was drawn: a photo, footage, a UI."""
from PIL import Image, ImageOps

import videobuilder as vb

from ...looks.fx import Filter, apply
from .. import _demo as demo
from ..schema import Technique


def _treat(im, t, age, u, shadow='#1d1b5c', highlight='#ffb26b', amount=1.0):
    gray = ImageOps.autocontrast(im.convert('L'), cutoff=1)
    inked = ImageOps.colorize(gray, shadow, highlight)
    return inked if amount >= 1 else Image.blend(im, inked, max(0.0, amount))


_FILTER = Filter('duotone', 'Duotone', 'two inks mapped onto the picture\'s brightness', _treat)


def duotone(cv, shadow='#1d1b5c', highlight='#ffb26b', amount=1.0, box=None):
    """A context manager: everything drawn on `cv` inside the block (and what
    was there already) is recoloured when it ends -- its darkest tones become
    `shadow`, its lightest `highlight`, the midtones a blend between them.
    `amount` (0..1) mixes from the original colours to the full duotone, to
    fade the treatment in; `box` (x, y, w, h) limits it to part of the frame.

        with duotone(cv, '#0b3d3a', '#f4e04d'):
            draw_the_shot(cv)
    """
    return apply(cv, _FILTER, 0.0, box=box,
                 opts={'shadow': shadow, 'highlight': highlight, 'amount': amount})


def _mix(a, b, p):
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return '#' + ''.join(f'{round(x + (y - x) * p):02x}' for x, y in zip(ca, cb))


PAIRS = (('#15193f', '#ff6f91'), ('#0b3d3a', '#f4e04d'))
SWATCHES = ('#e8202a', '#2fbf4a', '#2a6ef0', '#ffd23a')


def _scene(cv):
    """The photo with a row of saturated swatches, so the colour loss shows."""
    img = demo.photo()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))
    for i, c in enumerate(SWATCHES):
        demo.card(cv, demo.W * (0.5 + (i - 1.5) * 0.2), demo.H * 0.74, w=demo.W * 0.15, h=demo.H * 0.17, color=c)


def draw(n, cv):
    """Full colour; a divider sweeps the duotone across; then the ink pair changes."""
    p = vb.ease_in_out_quart(demo.phase(n, 0.4, 1.4))
    q = demo.phase(n, 1.9, 2.5)
    shadow, highlight = (_mix(PAIRS[0][i], PAIRS[1][i], q) for i in (0, 1))
    _scene(cv)
    x = demo.W * p
    if x > 1:
        with duotone(cv, shadow, highlight, box=(0, 0, x, demo.H)):
            pass  # nothing new to draw: treat what is already on the canvas
    if 0 < p < 1:
        cv.rect(x - 3, 0, 6, demo.H, '#ffffff', alpha=0.9)


TECHNIQUE = Technique(
    id='duotone',
    name='Duotone',
    family='vfx',
    group='Color & grading',
    aliases=('two-tone', 'gradient map', 'duo-tone'),
    definition='The image is reduced to its light and dark values and repainted in just two colours, '
               'one for the shadows and one for the highlights.',
    phrasings=('make the photo two colours, like a poster print',
               'tint the footage dark blue in the shadows and orange in the lights',
               'give the image that bold two-colour look'),
    related=('halftone', 'multiply-blend', 'ascii-art-render', 'dither-reveal', 'halftone-dot-scaling',
             'double-exposure'),
    api=('videobuilder.techniques.vfx.duotone.duotone',),
    demo=lambda: demo.film(draw),
)
