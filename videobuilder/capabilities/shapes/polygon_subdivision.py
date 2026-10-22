"""Polygon subdivision: a shape splits into smaller pieces of itself, level by
level -- new edges draw across each piece, then the pieces take their own
shades, until one polygon has become a fine mesh."""
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ...looks import kit as looks


def _mid(a, b):
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


def split(poly):
    """One subdivision step of the polygon `poly` (a list of (x, y)), as
    `(children, cuts)`. A triangle splits through its edge midpoints into four
    triangles; any other polygon splits from its centroid to its edge
    midpoints into one quad per corner. `cuts` are the new edges as
    `((x0, y0), (x1, y1))` pairs, each starting on the parent's boundary."""
    n = len(poly)
    mids = [_mid(poly[i], poly[(i + 1) % n]) for i in range(n)]
    if n == 3:
        children = [[poly[0], mids[0], mids[2]], [mids[0], poly[1], mids[1]],
                    [mids[2], mids[1], poly[2]], [mids[0], mids[1], mids[2]]]
        return children, [(mids[0], mids[1]), (mids[1], mids[2]), (mids[2], mids[0])]
    c = (sum(x for x, _ in poly) / n, sum(y for _, y in poly) / n)
    children = [[poly[i], mids[i], c, mids[i - 1]] for i in range(n)]
    return children, [(m, c) for m in mids]


def subdivide(poly, levels):
    """The pieces of `poly` after `levels` subdivision steps (see `split`), as
    a list of `(path, polygon)`: `path` is the tuple of child indices taken
    from the root, so a piece's colour or timing can key off it."""
    cells = [((), poly)]
    for _ in range(levels):
        cells = [(path + (i,), ch) for path, pl in cells for i, ch in enumerate(split(pl)[0])]
    return cells


def _shade(path, colours, seed):
    return colours[random.Random(f'{seed}:{path}').randrange(len(colours))]


def draw_subdivision(cv, poly, p, levels=4, colours=(demo.ACCENT, demo.TEAL), line=demo.BG, width=3,
                     seed=0, ease=vb.ease_in_out_quart):
    """Draw `poly` subdividing at progress `p` (0 -> 1) through `levels` steps.
    Each step takes an equal share of `p`: its cuts grow across every piece
    over the first 60%, then the new pieces fade in to their own colour (one
    of `colours`, picked per piece by `seed`). Edges are `line`, `width` px."""
    p = vb.clamp01(p)
    stage = min(int(p * levels), levels - 1)
    q = p * levels - stage
    grow, tint = ease(vb.clamp01(q / 0.6)), ease(vb.clamp01((q - 0.6) / 0.4))
    if p >= 1:
        stage, grow, tint = levels, 0.0, 0.0
    parents = subdivide(poly, stage)
    for path, pl in parents:
        looks.fill(cv, pl, _shade(path, colours, seed))
    for path, pl in parents:
        kids, cuts = split(pl)
        if tint > 0:
            for i, ch in enumerate(kids):
                looks.fill(cv, ch, _shade(path + (i,), colours, seed), alpha=tint)
        if grow > 0:
            for a, b in cuts:
                cv.line(a[0], a[1], a[0] + (b[0] - a[0]) * grow, a[1] + (b[1] - a[1]) * grow, line, width=width)
        if tint > 0:  # once pieces tint, keep their edges drawn over the new fill
            for ch in kids:
                looks.outline(cv, ch, line, width)
    for path, pl in parents:
        looks.outline(cv, pl, line, width)


def draw(n, cv):
    cx, cy, r = demo.W / 2, demo.H / 2 + 40, 300
    tri = [(cx, cy - r), (cx + r * 0.866, cy + r / 2), (cx - r * 0.866, cy + r / 2)]
    draw_subdivision(cv, tri, demo.phase(n, 0.3, 2.7), levels=4, width=2.5,
                     colours=(demo.ACCENT, demo.TEAL, '#f2b45a', '#3a7bd5'), seed=3)
    cv.mark('polygon', cx - r * 0.866, cy - r, r * 1.732, r * 1.5)


CAPABILITY = Capability(
    id='polygon-subdivision',
    name='Polygon subdivision',
    family='shapes',
    group='Polygon & tessellation',
    aliases=('polygon split', 'triangle subdivision', 'mesh subdivision', 'recursive polygon split'),
    definition='A single polygon is cut into smaller polygons, and each of those is cut again, '
               'step by step until the shape becomes a fine mosaic of pieces.',
    phrasings=('a triangle that keeps breaking into smaller triangles',
               'split the shape into pieces, then split those pieces again',
               'the polygon fractures into a finer and finer mesh'),
    related=('recursive-rectangle-subdivision', 'recursive-tree', 'shape-assemble-from-fragments',
             'shape-boolean-merge', 'koch-snowflake', 'tessellation-triangle-flip'),
    api=('videobuilder.capabilities.shapes.polygon_subdivision.draw_subdivision',
         'videobuilder.capabilities.shapes.polygon_subdivision.subdivide',
         'videobuilder.capabilities.shapes.polygon_subdivision.split'),
    demo=lambda: demo.film(draw),
)
