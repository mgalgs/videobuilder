"""Bayer ordered dithering: a picture's tones turned into a fixed, tiled
pattern of on/off pixels -- each pixel compared against its spot in a Bayer
threshold matrix -- so mid-greys come out as the familiar crosshatch."""
from contextlib import contextmanager
from functools import lru_cache

from PIL import Image, ImageChops

import videobuilder as vb

from .. import _demo as demo
from ...looks import fx
from ..schema import Technique
from ..typography.dither_reveal import bayer


@lru_cache(maxsize=8)
def _thresholds(w, h, order):
    """A w x h L image tiling the `2**order` Bayer matrix as levels 0..255."""
    m = bayer(order)
    k = len(m)
    tile = Image.frombytes('L', (k, k), bytes(int(v * 256) for row in m for v in row))
    out = Image.new('L', (w, h))
    for y in range(0, h, k):
        for x in range(0, w, k):
            out.paste(tile, (x, y))
    return out


def bayer_dither_image(im, cell=1, order=3, ink='#f4f4f2', paper='#14151a', gain=1.0):
    """The PIL image `im` as a two-tone Bayer dither, the same size: each
    `cell` x `cell` block of pixels becomes one dither pixel, `ink` where its
    brightness (times `gain`) beats its threshold in the tiled `2**order`
    matrix, `paper` elsewhere."""
    cell = max(1, int(round(cell)))
    w, h = im.size
    sw, sh = max(1, -(-w // cell)), max(1, -(-h // cell))
    tone = im.convert('L').resize((sw, sh), Image.BOX)
    if gain != 1.0:
        tone = tone.point(lambda v: min(255, int(v * gain)))
    mask = fx.threshold(ImageChops.subtract(tone, _thresholds(sw, sh, order)), 0)
    mask = mask.resize((sw * cell, sh * cell), Image.NEAREST).crop((0, 0, w, h))
    return Image.composite(Image.new('RGB', (w, h), ink), Image.new('RGB', (w, h), paper), mask)


_FILTER = fx.Filter('bayer-ordered-dithering', 'Bayer ordered dithering', 'tones as a tiled threshold pattern',
                    lambda im, t, age, u, **kw: bayer_dither_image(im, **kw))


@contextmanager
def bayer_dither(cv, box=None, cell=4, order=3, ink='#f4f4f2', paper='#14151a', gain=1.0):
    """Everything drawn inside the block comes out Bayer-dithered over `box`
    (x, y, w, h; default the whole frame): two inks, `ink` and `paper`, in
    dither pixels `cell` canvas px square from a `2**order` matrix.

        with bayer_dither(cv, box=(x, y, w, h)):
            draw_the_photo(cv)
    """
    k = cell * abs(cv.ctx.get_matrix().xx)
    opts = dict(cell=k, order=order, ink=ink, paper=paper, gain=gain)
    with fx.apply(cv, _FILTER, 0.0, box=box, opts=opts) as c:
        yield c


def draw(n, cv):
    img = demo.photo()
    bw, bh = 640, 420
    x, y = (demo.W - bw) / 2, (demo.H - bh) / 2
    # A dither edge sweeps left to right, then the whole frame holds dithered.
    edge = x + bw * vb.ease_in_out_quart(demo.phase(n, 0.4, 2.3))
    cv.image(img, x, y, bw, bh)
    if edge > x + 1:
        cv.ctx.save()
        cv.ctx.rectangle(x, y, edge - x, bh)
        cv.ctx.clip()
        with demo_dither(cv, (x, y, edge - x, bh)) as c:
            c.image(img, x, y, bw, bh)
        cv.ctx.restore()
        if edge < x + bw - 1:
            cv.line(edge, y, edge, y + bh, demo.ACCENT, width=3)
    cv.mark('photo', x, y, bw, bh)


def demo_dither(cv, box):
    return bayer_dither(cv, box=box, cell=3, ink=demo.INK, paper=demo.BG, gain=1.25)


TECHNIQUE = Technique(
    id='bayer-ordered-dithering',
    name='Bayer ordered dithering',
    family='vfx',
    group='Dithering & quantization',
    aliases=('Bayer dither', 'ordered dither', 'threshold matrix dither'),
    definition='The image is redrawn in just two colours, its shades of grey turned into a regular grid '
               'of dots and crosshatch checks that get denser where the picture is brighter.',
    phrasings=('make the photo look like an old 1-bit computer screen with that checkered dither',
               'turn the picture into a two-colour grid-pattern dither',
               'a retro Game Boy style crosshatch shading over the footage'),
    related=('pixel-sorting', 'dither-reveal', 'gradient-wipe', 'pixel-sort-text', 'pixelate-transition',
             'nearest-neighbor-upscale'),
    api=('videobuilder.techniques.vfx.bayer_ordered_dithering.bayer_dither',
         'videobuilder.techniques.vfx.bayer_ordered_dithering.bayer_dither_image',
         'videobuilder.techniques.typography.dither_reveal.bayer'),
    demo=lambda: demo.film(draw),
)
