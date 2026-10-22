"""Nearest-neighbor upscale: a small bitmap enlarged so each source pixel
becomes a hard-edged square block, with no smoothing between neighbours."""
import math

import cairo
from PIL import Image as PILImage

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def upscale_nearest(cv, img, x, y, w, h, alpha=1.0):
    """Draw the `vb.Image` `img` stretched to the box (x, y, w, h) with
    nearest-neighbour sampling: every source pixel lands as a crisp square
    (a rectangle when the box's aspect differs), never blurred or mip-mapped.
    `cv.image` is the smooth counterpart; use this one for pixel art, tiny
    sprites and deliberately low-res captures."""
    surf = img.level(0)
    c = cv.ctx
    c.save()
    c.translate(x, y)
    c.scale(w / img.w, h / img.h)
    c.set_source_surface(surf, 0, 0)
    pat = c.get_source()
    pat.set_filter(cairo.FILTER_NEAREST)
    pat.set_extend(cairo.EXTEND_PAD)
    c.rectangle(0, 0, img.w, img.h)
    c.clip()
    c.paint_with_alpha(alpha)
    c.restore()


SPRITE = (
    '....hhhhhh....',
    '..hhhhhhhhhh..',
    '.hhhhhhhhhhhh.',
    'hhhwwhhhhwwhhh',
    'hhwwkkhhwwkkhh',
    'hhwwkkhhwwkkhh',
    'hhhwwhhhhwwhhh',
    'hhhhhhhhhhhhhh',
    'hhhhhhhhhhhhhh',
    'hhhhhhhhhhhhhh',
    'hh.hhh..hhh.hh',
    'h...hh..hh...h',
)
_COLOURS = {'h': demo.ACCENT, 'w': '#ffffff', 'k': '#1b2a4a'}
_sprite = None


def _sprite_image():
    """The demo's 14x12 ghost as a `vb.Image`, built once."""
    global _sprite
    if _sprite is None:
        pil = PILImage.new('RGBA', (len(SPRITE[0]), len(SPRITE)), (0, 0, 0, 0))
        for j, row in enumerate(SPRITE):
            for i, ch in enumerate(row):
                if ch in _COLOURS:
                    r, g, b, _ = vb.rgba(_COLOURS[ch])
                    pil.putpixel((i, j), (round(r * 255), round(g * 255), round(b * 255), 255))
        _sprite = vb.Image.from_pil(pil)
    return _sprite


BIG = 24  # display px per sprite px at the end of the grow


def _draw(n, cv):
    img = _sprite_image()
    p = vb.ease_in_out_quart(demo.phase(n, 0.4, 2.3))
    s = math.exp(p * math.log(BIG))           # 1x -> BIG x, even in log steps
    w, h = img.w * s, img.h * s
    upscale_nearest(cv, img, demo.W / 2 - w / 2, demo.H / 2 - h / 2 - 20, w, h)
    demo.word(cv, f'{s:.0f}×', demo.W / 2, demo.H - 60, font=demo.mono(26), color=demo.MUTED)


TECHNIQUE = Technique(
    id='nearest-neighbor-upscale',
    name='Nearest-neighbor upscale',
    family='vfx',
    group='Pixel & mosaic',
    aliases=('nearest-neighbour scaling', 'point sampling', 'integer scaling', 'pixel-perfect scaling'),
    definition='A tiny image is blown up large by copying each of its pixels into a solid square, '
               'so it stays sharp and blocky instead of going soft.',
    phrasings=('make the pixel art bigger without it getting blurry',
               'scale this small sprite up and keep the hard square pixels',
               'zoom into the low-res picture so you can see every chunky pixel'),
    related=('gaussian-blur', 'blur-up-image-load', 'pixel-sorting', 'zoom-blur', 'image-hover-zoom',
             'pixelate-transition'),
    api=('videobuilder.techniques.vfx.nearest_neighbor_upscale.upscale_nearest',),
    demo=lambda: demo.film(_draw),
)
