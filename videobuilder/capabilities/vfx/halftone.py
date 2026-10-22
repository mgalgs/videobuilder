"""Halftone: the picture is reprinted as a screen of dots on a regular grid,
each dot as big as its patch of the picture is dark, like a newspaper photo."""
from contextlib import contextmanager

import videobuilder as vb
from PIL import Image, ImageChops

from .. import _demo as demo
from ...looks import fx
from ..schema import Capability


def halftone_image(im, pitch, ink='#141414', paper='#f2ede2', light=False, soft=6, dx=0.0, dy=0.0):
    """The PIL RGB image `im` as a halftone: dots on a 45-degree grid
    `pitch` px apart, `ink` dots on `paper`. A dot grows with how dark its
    patch is (with `light`, how bright: light dots on a dark ground, as on a
    screen). `ink=None` prints each dot in the picture's own colour. `soft`
    sharpens the dot edges (higher is crisper); `dx`, `dy` slide the screen."""
    tone = fx.luma(im)
    if not light:
        tone = ImageChops.invert(tone)
    screen = fx.screen(im.width, im.height, pitch, dx, dy)
    mask = ImageChops.subtract(tone, screen).point(lambda v: min(255, v * soft))
    dots = im if ink is None else Image.new('RGB', im.size, ink)
    return Image.composite(dots, Image.new('RGB', im.size, paper), mask)


@contextmanager
def halftone(cv, pitch=14, box=None, **kw):
    """A context manager: everything on `cv` when the block ends -- what was
    there before and what the block draws -- is reprinted as a halftone,
    `pitch` frame px between dots (or only inside `box`, (x, y, w, h)).
    `kw` goes to `halftone_image` (`ink`, `paper`, `light`, `soft`, `dx`, `dy`).

        with halftone(cv, pitch=12):
            draw_the_photo(cv)
        # copy that must stay readable goes here
    """
    def treat(im, t, age, u):
        k = dict(kw)
        k['dx'], k['dy'] = k.get('dx', 0.0) * u, k.get('dy', 0.0) * u
        return halftone_image(im, max(2.0, pitch * u), **k)
    with fx.apply(cv, fx.Filter('halftone', 'Halftone', 'a print screen of dots', treat), 0.0, box=box):
        yield cv


def draw(n, cv):
    img = demo.photo()
    p = demo.phase(n, 0.5, 2.3)
    if p <= 0:
        cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))
        return
    # the screen coarsens from a fine print to big newspaper dots
    with halftone(cv, pitch=6 + 22 * vb.ease_in_out_quart(p)):
        cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))
    cv.mark('picture', 0, 0, demo.W, demo.H)


CAPABILITY = Capability(
    id='halftone',
    name='Halftone',
    family='vfx',
    group='Dithering & quantization',
    aliases=('newsprint dots', 'halftone dots', 'print screen'),
    definition='The image turns into a grid of ink dots that swell in the dark areas and shrink '
               'to specks in the light ones, like a photo printed in a newspaper.',
    phrasings=('make the picture look like it was printed in a newspaper, all dots',
               'turn the photo into a pattern of dots that get bigger where it is darker',
               'a comic-print dot screen over the footage'),
    related=('halftone-dot-scaling', 'duotone', 'dither-reveal', 'ink-splash-spread', 'dot-matrix-text',
             'dot-density-map'),
    api=('videobuilder.capabilities.vfx.halftone.halftone',
         'videobuilder.capabilities.vfx.halftone.halftone_image',
         'videobuilder.looks.fx.halftone'),
    demo=lambda: demo.film(draw),
)
