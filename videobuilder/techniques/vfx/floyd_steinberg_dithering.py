"""Floyd-Steinberg dithering: the picture cut down to a handful of flat
colours, the shading it loses rebuilt by scattering pixels of those colours
-- each pixel's rounding error pushed on to its unvisited neighbours, so
smooth tones turn into a fine, wormy speckle."""
from contextlib import contextmanager

from PIL import Image

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ...looks.fx import Filter, apply, palette_image, posterize

ONE_BIT = ('#000000', '#ffffff')


def fs_dither(im, colours=ONE_BIT, pixel=1):
    """The PIL image `im` reduced to `colours` ('#rrggbb') by Floyd-Steinberg
    error diffusion, as RGB the same size. `pixel`: how many image px one
    dither pixel covers, so the speckle can be made chunky and visible."""
    pixel = max(1, round(pixel))
    w, h = im.size
    small = im.convert('RGB')
    if pixel > 1:
        small = small.resize((max(1, -(-w // pixel)), max(1, -(-h // pixel))), Image.BOX)
    out = posterize(small, palette_image(colours), dither=True).convert('RGB')
    if pixel > 1:
        out = out.resize((out.width * pixel, out.height * pixel), Image.NEAREST).crop((0, 0, w, h))
    return out


@contextmanager
def floyd_steinberg(cv, colours=ONE_BIT, pixel=4, box=None):
    """Everything drawn on `cv` inside the block (and whatever was there
    already) is Floyd-Steinberg dithered to `colours` when the block ends.
    `pixel`: dither pixel size in frame px at 1080; `box`: (x, y, w, h) in
    frame px to treat only part of the frame.

        with floyd_steinberg(cv, ('#101418', '#e9e6df'), pixel=4):
            cv.image(img, *box)
    """
    flt = Filter('floyd-steinberg', 'Floyd-Steinberg dither', 'error-diffused flat colours',
                 lambda im, t, age, u: fs_dither(im, colours, pixel * u))
    with apply(cv, flt, 0.0, box=box):
        yield cv


PALETTE = ('#14161c', '#e9e6df')


def draw(n, cv):
    img = demo.photo()
    frame = vb.Box.of(cv).cover(img.w, img.h)
    with floyd_steinberg(cv, PALETTE, pixel=4):          # the whole frame, so the speckle never shimmers
        cv.image(img, *frame)
    x = demo.W * (1 - vb.ease_in_out_quart(demo.phase(n, 0.3, 2.2)))
    if x > 0:                                            # the original, shrinking back to the left
        c = cv.ctx
        c.save()
        c.rectangle(0, 0, x, demo.H)
        c.clip()
        cv.image(img, *frame)
        c.restore()
        if x < demo.W:
            cv.line(x, 0, x, demo.H, demo.ACCENT, width=6)
    cv.mark('photo', 0, 0, demo.W, demo.H)


TECHNIQUE = Technique(
    id='floyd-steinberg-dithering',
    name='Floyd-Steinberg dithering',
    family='vfx',
    group='Dithering & quantization',
    aliases=('error diffusion dithering', 'error diffusion', '1-bit dither', 'FS dither'),
    definition='An image is reduced to a few flat colours, and the tones it loses come back as a fine '
               'scatter of pixels, each pixel passing its colour error on to its neighbours.',
    phrasings=('make the photo look like an old black-and-white Mac screen',
               'turn the picture into a two-colour pixel speckle that still shows the shading',
               'give it that grainy 1-bit dithered look'),
    related=('fractal-brownian-motion', 'film-grain', 'domain-warping', 'gaussian-blur', 'blur-up-image-load',
             'curl-noise-flow'),
    api=('videobuilder.techniques.vfx.floyd_steinberg_dithering.floyd_steinberg',
         'videobuilder.techniques.vfx.floyd_steinberg_dithering.fs_dither',
         'videobuilder.looks.fx.posterize'),
    demo=lambda: demo.film(draw),
)
