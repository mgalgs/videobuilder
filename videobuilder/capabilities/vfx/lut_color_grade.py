"""LUT color grade: every colour in the picture is sent through one fixed
colour lookup table, so the whole frame takes on a styled look -- here a
teal-and-orange grade (cool shadows, warm highlights, a little extra punch).

    with lut_grade(cv, amount=p):        # everything on cv so far, and drawn inside, is graded
        draw_the_shot(n, cv)

The table is a real 3D LUT (Pillow's `Color3DLUT`), built once from a plain
`(r, g, b) -> (r, g, b)` function by `make_lut`, so a film can grade with its
own look as easily as with `TEAL_ORANGE`. The pixel plumbing is the filter
looks' (`looks.fx.apply`).
"""
import math
from functools import lru_cache

from PIL import Image, ImageFilter

import videobuilder as vb

from .. import _demo as demo
from ...looks.fx import Filter, apply
from ..schema import Capability


def teal_orange(r, g, b):
    """The teal-and-orange grade on one colour (channels 0..1): an S-curve
    for contrast, shadows pushed toward teal, highlights toward orange, and
    saturation nudged up."""
    luma = 0.299 * r + 0.587 * g + 0.114 * b
    curved = 0.5 - 0.5 * math.cos(math.pi * luma)          # gentle S-curve on brightness
    shade = (1 - curved) ** 1.5                               # how much of the teal goes in
    light = curved ** 1.5                                     # how much of the orange goes in
    out = []
    for c, teal, orange in zip((r, g, b), (0.0, 0.36, 0.46), (1.0, 0.58, 0.22)):
        c = luma + (c - luma) * 1.4                           # more saturation
        c += 1.3 * (curved - luma)                            # carry the contrast curve
        c = c * (1 - 0.6 * shade) + teal * 0.6 * shade
        c = c * (1 - 0.55 * light) + orange * 0.55 * light
        out.append(min(1.0, max(0.0, c)))
    return tuple(out)


@lru_cache(maxsize=None)
def make_lut(grade=teal_orange, size=17):
    """A 3D colour lookup table (`size` points per channel) sampling
    `grade(r, g, b) -> (r, g, b)`, channels 0..1. Cached per grade."""
    return ImageFilter.Color3DLUT.generate(size, grade)


def __getattr__(name):
    # TEAL_ORANGE is built on first use (`make_lut` caches it), not at import.
    if name == 'TEAL_ORANGE':
        return make_lut()
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')


def grade_image(im, lut=None, amount=1.0):
    """A PIL RGB image sent through `lut`, mixed `amount` (0..1) of the way
    from the original to the fully graded picture. `lut` defaults to
    `TEAL_ORANGE`."""
    if amount <= 0:
        return im
    lut = make_lut() if lut is None else lut
    graded = im.convert('RGB').filter(lut)
    return graded if amount >= 1 else Image.blend(im.convert('RGB'), graded, amount)


def lut_grade(cv, lut=None, amount=1.0, box=None):
    """A context manager: what is on `cv` already, and everything drawn
    inside the block, goes through the colour lookup table `lut` when the
    block ends -- every pixel, or only those in `box` ((x, y, w, h), frame
    px). `amount` (0..1) dials the grade in: animate it to fade the look up,
    or animate `box` to wipe it across. Draw copy that must keep its own
    colours after the block. `lut` defaults to `TEAL_ORANGE`."""
    flt = Filter('lut-grade', 'LUT color grade', 'colours remapped through a lookup table',
                 lambda im, t, age, u: grade_image(im, lut, amount))
    return apply(cv, flt, 0.0, box=box)


# ---- the demo: an ungraded photo, the grade wiping across it, then the graded shot ----

def _tag(cv, text, x, y, right=False):
    f = demo.mono(24, 700)
    w, h = vb.text.block_size([text], f)
    x = x - w - 28 if right else x
    cv.rect(x, y, w + 28, h + 16, '#000000', radius=10, alpha=0.55)
    vb.text.draw(cv, [text], f, x + 14, y + 8, demo.INK)


def draw(n, cv):
    img = demo.photo()
    p = vb.ease_in_out_quart(demo.phase(n, 0.7, 2.1))
    edge = demo.W * p
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))
    if edge > 1:
        with lut_grade(cv, box=(0, 0, edge, demo.H)):
            pass
    if 0 < p < 1:
        cv.line(edge, 0, edge, demo.H, demo.INK, width=3, alpha=0.9)
    if p < 0.97:
        _tag(cv, 'ORIGINAL', demo.W - 40, 36, right=True)
    if p > 0.03:
        _tag(cv, 'LUT: TEAL & ORANGE', 40, 36)


CAPABILITY = Capability(
    id='lut-color-grade',
    name='LUT color grade',
    family='vfx',
    group='Color & grading',
    aliases=('color look-up table', 'lookup grade', 'color grade shift', 'teal and orange'),
    definition='Each colour in the shot is swapped for its entry in one fixed table, '
               'giving the whole picture a consistent styled look such as cool shadows and warm highlights.',
    phrasings=('give the footage a cinematic teal-and-orange grade',
               'put a film look on the shot',
               'colour grade the video so it feels moodier',
               'apply a LUT to the clip'),
    related=('luma-wipe', 'shine-glint-sweep', 'palette-shift-transition', 'theme-swap-crossfade',
             'hue-cycle-fill', 'gradient-sweep-across-text'),
    api=('videobuilder.capabilities.vfx.lut_color_grade.lut_grade',
         'videobuilder.capabilities.vfx.lut_color_grade.make_lut',
         'videobuilder.capabilities.vfx.lut_color_grade.grade_image'),
    demo=lambda: demo.film(draw),
)
