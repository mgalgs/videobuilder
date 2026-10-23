"""Pixelation: the picture is broken into large square cells, each painted
one flat colour -- the average of what it covers -- so detail drops out and
only a blocky mosaic of the image is left.

`Canvas.pixelated` already gives a pixel-art layer, but it draws at low
resolution, so each cell takes the colour under one point of the scene.
`pixelate` here renders the scene sharp first and averages each cell, the
look of a downsampled frame or a censor mosaic."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def pixelate(cv, scene, block, x=0.0, y=0.0, w=None, h=None):
    """Draw `scene(cv)` pixelated into `block`-px square cells over the region
    (x, y, w, h) (default the whole frame): the scene is rendered at full
    detail, each cell is filled with the average colour it covers, and the
    cells are painted back hard-edged. Outside the region the scene is not
    drawn. `block` need not be a whole number; at 1 or less the scene draws
    as is. Animate `block` (from 1 up to tens of px and back) to pixelate a
    shot out and in, or keep it fixed to hide a face or a plate."""
    w = cv.width - x if w is None else w
    h = cv.height - y if h is None else h
    if block <= 1:
        with cv.clip(x, y, w, h):
            scene(cv)
        return
    m = cv.ctx.get_matrix()
    sharp = vb.Canvas(cv.width, cv.height, scale=cv.scale, format=cv.format)
    sharp.ctx.set_matrix(m)
    scene(sharp)
    sharp.surface.flush()
    gw, gh = max(1, math.ceil(w / block)), max(1, math.ceil(h / block))
    cells = cairo.ImageSurface(cairo.FORMAT_ARGB32, gw, gh)
    c = cairo.Context(cells)
    c.scale(1 / block, 1 / block)            # one cell px is `block` frame px ...
    c.translate(-x, -y)                     # ... starting at the region's corner ...
    inv = cairo.Matrix(*m)
    inv.invert()
    c.transform(inv)                        # ... read from the sharp render's device px
    c.set_source_surface(sharp.surface, 0, 0)
    pat = c.get_source()
    pat.set_filter(cairo.FILTER_BEST)       # averages every source px a cell covers ...
    pat.set_extend(cairo.EXTEND_PAD)        # ... and a cell past the frame edge repeats the edge, not transparent black
    c.paint()
    cells.flush()
    out = cv.ctx
    out.save()
    out.translate(x, y)
    out.scale(block, block)
    out.set_source_surface(cells, 0, 0)
    out.get_source().set_filter(cairo.FILTER_NEAREST)
    out.rectangle(0, 0, w / block, h / block)
    out.clip()
    out.paint()
    out.restore()


COARSEST = 40      # cell size at the peak, film px


def _block(n):
    """Sharp, then cells growing geometrically to `COARSEST`, a hold, then
    back down to sharp."""
    up = demo.phase(n, 0.4, 1.3)
    down = demo.phase(n, 1.8, 2.7)
    d = vb.ease_in_out_quart(up) * (1 - vb.ease_in_out_quart(down))
    return COARSEST ** d


def scene(cv):
    img = demo.photo()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))
    demo.card(cv, demo.W * 0.68, demo.H * 0.62, w=300, h=180)


def draw(n, cv):
    pixelate(cv, scene, round(_block(n)))


CAPABILITY = Capability(
    id='pixelation',
    name='Pixelation',
    family='vfx',
    group='Pixel & mosaic',
    aliases=('mosaic pixelate', 'block pixelation', 'pixel effect', 'low-res downsample', 'lo-fi downsample',
             'mosaic', 'pixelize'),
    definition='The frame is chopped into big square tiles and each tile shows just the average colour '
               'underneath it, so the picture turns into a coarse, blocky version of itself.',
    phrasings=('make the image go all blocky and low-res',
               'pixelate the shot so you can only make out big squares of colour',
               'put a mosaic over it like a censored face'),
    related=('pixelate-transition', 'pixelation-reveal', 'pixel-sorting', 'blur-up-image-load', 'gaussian-blur',
             'pixel-build'),
    api=('videobuilder.capabilities.vfx.pixelation.pixelate', 'videobuilder.Canvas.pixelated'),
    demo=lambda: demo.film(draw),
)
