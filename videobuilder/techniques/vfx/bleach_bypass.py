"""Bleach bypass: a film-lab grade that keeps a silver image laid over the
colour one, so the picture loses much of its colour while its contrast
climbs -- darker shadows, hotter highlights, a hard, metallic look."""
from contextlib import contextmanager

import videobuilder as vb
from PIL import Image, ImageChops, ImageEnhance

from .. import _demo as demo
from ..schema import Technique
from ...looks import fx


def bleach_bypass_image(im, amount=1.0, desaturate=0.55, silver=0.6, contrast=1.25):
    """`im` (a PIL RGB image) with the bleach-bypass grade at strength
    `amount` (0 = untouched, 1 = full): the colour pulled `desaturate` of the
    way toward grey, its own luminance overlaid on it at `silver` strength
    (the retained silver of the film process), and the contrast pushed by
    `contrast`."""
    if amount <= 0:
        return im
    im = im.convert('RGB')
    grey = im.convert('L')
    faded = Image.blend(im, Image.merge('RGB', (grey,) * 3), desaturate)
    graded = Image.blend(faded, ImageChops.overlay(faded, Image.merge('RGB', (grey,) * 3)), silver)
    graded = ImageEnhance.Contrast(graded).enhance(contrast)
    return graded if amount >= 1 else Image.blend(im, graded, amount)


@contextmanager
def bleach_bypassed(cv, amount=1.0, box=None, **opts):
    """Everything drawn inside the block gets the bleach-bypass grade at
    strength `amount`, over the whole frame or the region `box` (x, y, w, h):

        with bleach_bypassed(cv, 0.8):
            draw_the_shot(n, cv)

    `opts` pass through to `bleach_bypass_image`."""
    flt = fx.Filter('bleach-bypass', 'Bleach bypass', 'desaturated, high-contrast grade',
                    lambda im, t, age, u: bleach_bypass_image(im, amount, **opts))
    with fx.apply(cv, flt, 0.0, box=box) as c:
        yield c


def _shot(cv):
    img = demo.photo()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))


def _draw(n, cv):
    # The grade wipes across the photo left to right, then the whole frame holds graded.
    p = vb.ease_in_out_quart(demo.phase(n, 0.5, 2.1))
    _shot(cv)
    edge = demo.W * p
    if edge > 1:
        with bleach_bypassed(cv, box=(0, 0, edge, demo.H)) as c:
            _shot(c)
    if 0 < p < 1:
        cv.line(edge, 0, edge, demo.H, demo.INK, width=4, alpha=0.9)


TECHNIQUE = Technique(
    id='bleach-bypass',
    name='Bleach bypass',
    family='vfx',
    group='Color & grading',
    aliases=('bleach bypass look', 'skip-bleach grade', 'silver retention'),
    definition='The picture is graded so its colours go muted and steely while the contrast is pushed hard, '
               'with deep blacks and bright, harsh highlights.',
    phrasings=('make it look gritty and washed out but punchy',
               'drain most of the colour and crank the contrast, like a war movie',
               'give the footage that harsh, silvery desaturated grade'),
    related=('theme-swap-crossfade', 'difference-blend', 'gradient-sweep-across-text', 'chroma-bleed',
             'oil-paint-filter', 'unsharp-mask'),
    api=('videobuilder.techniques.vfx.bleach_bypass.bleach_bypassed',
         'videobuilder.techniques.vfx.bleach_bypass.bleach_bypass_image'),
    demo=lambda: demo.film(_draw),
)
