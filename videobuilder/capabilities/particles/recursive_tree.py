"""Recursive tree: a single trunk grows, then forks into two shorter, thinner
branches at a set angle, and every branch forks again the same way, level by
level, until the canopy ends in a fan of fine twigs."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def branches(x, y, length, depth, heading=-math.pi / 2, spread=math.radians(32), ratio=0.7, bend=0.0):
    """The segments of a binary fractal tree rooted at (x, y), as a list of
    `(level, (x0, y0), (x1, y1))` ordered by level, trunk first. The trunk is
    `length` px long pointing along `heading` (radians, canvas convention, so
    `-pi/2` is up); each branch splits into two children turned `spread` either
    side and `ratio` times as long, `depth` levels in all. `bend` adds to every
    child's turn, so a small value leans the whole tree like wind."""
    out = []
    tips = [(x, y, heading)]
    for level in range(depth):
        size = length * ratio ** level
        grown = []
        for tx, ty, a in tips:
            ex, ey = tx + size * math.cos(a), ty + size * math.sin(a)
            out.append((level, (tx, ty), (ex, ey)))
            grown += [(ex, ey, a - spread + bend), (ex, ey, a + spread + bend)]
        tips = grown
    return out


def draw_tree(cv, x, y, p, length=150, depth=8, spread=math.radians(32), ratio=0.7, width=12,
              color=demo.INK, tip=demo.ACCENT, bend=0.0, ease=vb.ease_out_quint):
    """Draw the tree of `branches` growing at progress `p` (0 -> 1): the levels
    grow out one after another, each taking an equal share of `p` and easing
    out from its parent's end. Strokes thin by `ratio` per level from `width`
    and shade from `color` towards `tip`; the finished twigs get small `tip` buds."""
    p = vb.clamp01(p)
    segs = branches(x, y, length, depth, spread=spread, ratio=ratio, bend=bend)
    c = cv.ctx
    c.save()
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    ink, hi = vb.rgba(color), vb.rgba(tip)
    for level, (x0, y0), (x1, y1) in segs:
        g = ease(vb.clamp01(p * depth - level))
        if g <= 0:
            continue
        k = (level / (depth - 1)) ** 2 if depth > 1 else 0
        c.set_source_rgba(*(ink[i] + (hi[i] - ink[i]) * k for i in range(3)), ink[3])
        c.set_line_width(max(1.2, width * ratio ** level))
        c.move_to(x0, y0)
        c.line_to(x0 + (x1 - x0) * g, y0 + (y1 - y0) * g)
        c.stroke()
        if level == depth - 1:
            demo.dot(cv, x1, y1, 2.5 * g, color=tip, alpha=g)
    c.restore()


def draw(n, cv):
    p = demo.phase(n, 0.2, 2.5)
    sway = 0.03 * math.sin(n / demo.FPS * 2.2) * demo.phase(n, 2.3, 2.8)
    draw_tree(cv, demo.W / 2, demo.H - 40, p, bend=sway)
    cv.mark('tree', demo.W / 2 - 270, 40, 540, demo.H - 80)


CAPABILITY = Capability(
    id='recursive-tree',
    name='Recursive tree',
    family='particles',
    group='Growth & L-systems',
    aliases=('fractal tree', 'binary tree'),
    definition='A trunk grows and forks into two smaller branches, and each of those forks again at the same '
               'angle and scale, level after level, until a full branching canopy has drawn itself.',
    phrasings=('grow a fractal tree that keeps splitting into smaller branches',
               'a branching tree that draws itself from the trunk up',
               'lines that fork in two over and over like a tree'),
    related=('polygon-subdivision', 'decision-tree-branch-growth', 'recursive-rectangle-subdivision',
             'treemap-re-layout', 'diffusion-limited-aggregation', 'org-chart-grow'),
    api=('videobuilder.capabilities.particles.recursive_tree.draw_tree',
         'videobuilder.capabilities.particles.recursive_tree.branches'),
    demo=lambda: demo.film(draw),
)
