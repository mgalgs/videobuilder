"""Skeleton Shimmer: grey placeholder blocks stand in for content that is
still loading, and a soft band of light sweeps across them, over and over."""
import math

import cairo

import videobuilder as vb
from videobuilder.canvas import _rounded, rgba

from .. import _demo as demo
from ..schema import Capability


def skeleton_shimmer(cv, blocks, p, base='#2a2c33', highlight='#3d4049', band=0.35, tilt=20):
    """Draw placeholder `blocks` with a highlight band at sweep progress `p`
    (0 -> 1 is one pass, left to right; feed it `t / period % 1` to loop).

    `blocks` are `(x, y, w, h)` or `(x, y, w, h, radius)`; a radius of half the
    short side makes a pill or a circle. The band is one sweep across the
    blocks' joint bounds, so every block lights up in turn like one surface.
    `band` is the band's width as a fraction of those bounds, `tilt` its lean
    in degrees. Returns the Box of the bounds."""
    rects = [(b[0], b[1], b[2], b[3], b[4] if len(b) > 4 else min(b[2], b[3]) * 0.2) for b in blocks]
    x0, y0 = min(r[0] for r in rects), min(r[1] for r in rects)
    x1, y1 = max(r[0] + r[2] for r in rects), max(r[1] + r[3] for r in rects)
    bw = band * (x1 - x0)
    centre = x0 - bw + vb.clamp01(p) * (x1 - x0 + 2 * bw)
    dx, dy = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
    c = cv.ctx
    c.save()
    for x, y, w, h, r in rects:
        _rounded(c, x, y, w, h, r)
    c.clip()
    c.set_source_rgba(*rgba(base))
    c.paint()
    cy = (y0 + y1) / 2
    g = cairo.LinearGradient(centre - dx * bw / 2, cy - dy * bw / 2, centre + dx * bw / 2, cy + dy * bw / 2)
    hl = rgba(highlight)
    for stop, a in ((0, 0), (0.5, 1), (1, 0)):
        g.add_color_stop_rgba(stop, hl[0], hl[1], hl[2], hl[3] * a)
    c.set_source(g)
    c.paint()
    c.restore()
    return vb.Box(x0, y0, x1 - x0, y1 - y0)


def _blocks():
    """A feed of three loading rows: an avatar circle, a title line, two text lines."""
    out, left, top, row = [], 200, 140, 120
    for i in range(3):
        y = top + i * row
        out.append((left, y, 76, 76, 38))
        out.append((left + 100, y + 4, 260 - 40 * (i % 2), 20, 10))
        out.append((left + 100, y + 36, 460, 14, 7))
        out.append((left + 100, y + 60, 360 - 50 * i, 14, 7))
    return out


def draw(n, cv):
    demo.word(cv, 'Loading…', demo.W / 2, 80, size=30, color=demo.MUTED, weight=600)
    box = skeleton_shimmer(cv, _blocks(), (n / demo.FPS / 1.4) % 1, base=demo.LINE, highlight='#5a5f6c')
    cv.mark('skeleton', *box)


CAPABILITY = Capability(
    id='skeleton-shimmer',
    name='Skeleton shimmer',
    family='ui',
    group='Loaders',
    aliases=('skeleton screen', 'skeleton loader', 'shimmer placeholder', 'content placeholder'),
    definition='Flat grey shapes sketch out where text and images will appear, while a soft strip of '
               'light glides across them again and again to show the page is still loading.',
    phrasings=('grey placeholder bars with a shine moving over them while it loads',
               'a loading state that shows the layout as blank blocks with a sweeping gleam',
               'like the empty shimmering cards an app shows before the feed arrives'),
    related=('text-reflection-shimmer', 'chrome-specular-shimmer', 'gooch-shading', 'scroll-pin-section',
             'scroll-linked-background-shift', 'bookmark-fill'),
    api=('videobuilder.capabilities.ui.skeleton_shimmer.skeleton_shimmer',),
    demo=lambda: demo.film(draw),
)
