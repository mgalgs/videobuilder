"""Pixelation Reveal: the subject first shows as a few big flat blocks of its
own averaged colours, and the blocks halve in size, step by step, until the
picture is sharp."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def block_size(p, block=64, steps=6):
    """The mosaic block size in film px at progress `p` (0 -> 1): `block` at
    0, shrinking geometrically through `steps` hard steps, and 1 (sharp) for
    the last step. `steps=0` shrinks smoothly instead."""
    p = vb.clamp01(p)
    if steps == 0:
        return block ** (1 - p)
    return block ** (1 - min(steps, int(p * (steps + 1))) / steps)


def mosaic(cv, draw, size, x=0.0, y=0.0, w=None, h=None, alpha=1.0):
    """`draw(c)` as a mosaic over the region (x, y, w, h) (default the whole
    frame): each `size` x `size` block is one flat tile of the average colour
    under it. `draw` uses frame coordinates on the canvas it is given. A
    `size` at or under one device pixel just draws it sharp."""
    w = cv.width if w is None else w
    h = cv.height if h is None else h
    s = cv.scale_factor()
    if size * s <= 1:
        with cv.layer(opacity=alpha):
            draw(cv)
        return
    full = vb.Canvas(w, h, scale=s, format=cv.format)
    with full.layer(dx=-x, dy=-y):
        draw(full)
    full.surface.flush()
    nx, ny = math.ceil(w / size), math.ceil(h / size)
    small = cairo.ImageSurface(cairo.FORMAT_ARGB32, nx, ny)
    c = cairo.Context(small)
    c.scale(1 / (size * s), 1 / (size * s))
    c.set_source_surface(full.surface, 0, 0)
    c.get_source().set_filter(cairo.FILTER_GOOD)   # area-averages when shrinking
    c.paint()
    small.flush()
    c = cv.ctx
    c.save()
    c.translate(x, y)
    c.rectangle(0, 0, w, h)
    c.clip()
    c.scale(size, size)
    c.set_source_surface(small, 0, 0)
    c.get_source().set_filter(cairo.FILTER_NEAREST)
    c.paint_with_alpha(alpha)
    c.restore()


def pixelation_reveal(cv, draw, p, x=0.0, y=0.0, w=None, h=None, block=64, steps=6, fade=0.15):
    """Reveal `draw(c)` at progress `p` (0 -> 1): it fades in as coarse
    `block`-px tiles over the first `fade` of the move, then the tiles step
    down in size (`block_size`) until it is drawn sharp at 1. The region and
    `draw` work as in `mosaic`. Run `1 - p` to pixelate something away."""
    p = vb.clamp01(p)
    alpha = 1.0 if fade <= 0 else vb.clamp01(p / fade)
    if alpha <= 0:
        return
    mosaic(cv, draw, block_size(p, block, steps), x, y, w, h, alpha=alpha)


TEXT = 'PIXEL PERFECT'


def subject(cv):
    f = demo.font(96, 900)
    box = demo.word(cv, TEXT, demo.W / 2, demo.H / 2 - 20, font=f)
    cv.rect(box.x, box.y + box.h + 14, box.w * 0.45, 14, demo.ACCENT, radius=7)
    cv.rect(box.x + box.w * 0.5, box.y + box.h + 14, box.w * 0.5, 14, demo.TEAL, radius=7)
    return box


def draw(n, cv):
    pixelation_reveal(cv, subject, demo.phase(n, 0.3, 2.4), 0, demo.H * 0.2, demo.W, demo.H * 0.6, block=64)
    f = demo.font(96, 900)
    w, h = vb.text.block_size([TEXT], f)
    cv.mark('text', (demo.W - w) / 2, demo.H / 2 - 20 - h / 2, w, h)


CAPABILITY = Capability(
    id='pixelation-reveal',
    name='Pixelation reveal',
    family='typography',
    group='Masking and clipping',
    aliases=('depixelate', 'mosaic reveal', 'pixelate in', 'resolve from pixels'),
    definition='A title starts as a handful of large flat colour squares and sharpens as the squares '
               'get smaller and smaller, until the crisp words are left.',
    phrasings=('the text starts blocky and pixelated and then sharpens into focus',
               'reveal the headline by de-pixelating it',
               'big chunky squares that resolve into the logo'),
    related=('pixelate-transition', 'pixel-sort-text', 'pixelation', 'text-mask-reveal', 'pixel-build',
             'noise-dissolve'),
    api=('videobuilder.capabilities.typography.pixelation_reveal.pixelation_reveal',
         'videobuilder.capabilities.typography.pixelation_reveal.mosaic',
         'videobuilder.capabilities.typography.pixelation_reveal.block_size'),
    demo=lambda: demo.film(draw),
)
