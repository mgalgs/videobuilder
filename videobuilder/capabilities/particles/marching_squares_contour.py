"""Marching squares contour: a smooth field (here, a few drifting metaballs)
is sampled on a square grid, and each grid cell is cut where the field
crosses a threshold, so the cells together trace one outline around every
region above it. Blobs that drift close fuse into one outline and split
apart again."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

# Each corner of a cell (tl, tr, br, bl) and the two edges that meet at it,
# as indices into the crossings (top, right, bottom, left).
_CORNER_EDGES = ((3, 0), (0, 1), (1, 2), (2, 3))


def marching_squares(field, x, y, w, h, cell, level=1.0):
    """Trace where `field(px, py)` crosses `level` across the box (x, y, w, h),
    sampled every `cell` px. Returns `(segments, patches)`: `segments` is a
    list of ((x0, y0), (x1, y1)) contour pieces, one or two per crossed cell,
    with ends interpolated linearly along the cell edges; `patches` is a list
    of point lists, the part of each cell at or above `level` (whole cells
    included), which filled together cover the inside of the contour.
    Ambiguous (saddle) cells are settled by the field at the cell's centre."""
    cols, rows = max(1, math.ceil(w / cell)), max(1, math.ceil(h / cell))
    xs = [x + i * w / cols for i in range(cols + 1)]
    ys = [y + j * h / rows for j in range(rows + 1)]
    v = [[field(px, py) for px in xs] for py in ys]

    def cut(p, q, a, b):
        t = 0.5 if a == b else (level - a) / (b - a)
        return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)

    segments, patches = [], []
    for j in range(rows):
        for i in range(cols):
            pts = ((xs[i], ys[j]), (xs[i + 1], ys[j]), (xs[i + 1], ys[j + 1]), (xs[i], ys[j + 1]))
            vals = (v[j][i], v[j][i + 1], v[j + 1][i + 1], v[j + 1][i])
            inside = [a >= level for a in vals]
            if not any(inside):
                continue
            if all(inside):
                patches.append(list(pts))
                continue
            # Crossings on the top, right, bottom and left edges (None where uncut).
            cross = [cut(pts[k], pts[(k + 1) % 4], vals[k], vals[(k + 1) % 4])
                     if inside[k] != inside[(k + 1) % 4] else None for k in range(4)]
            saddle = inside == [True, False, True, False] or inside == [False, True, False, True]
            joined = saddle and field((xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2) >= level
            if saddle:
                # The contour isolates two corners: the inside ones, unless the
                # centre is inside, when it isolates the outside ones.
                alone = [k for k in range(4) if inside[k] != joined]
                for k in alone:
                    e0, e1 = _CORNER_EDGES[k]
                    segments.append((cross[e0], cross[e1]))
            else:
                segments.append(tuple(q for q in cross if q))
            if saddle and not joined:
                for k in alone:
                    e0, e1 = _CORNER_EDGES[k]
                    patches.append([cross[e0], pts[k], cross[e1]])
            else:
                poly = []
                for k in range(4):
                    if inside[k]:
                        poly.append(pts[k])
                    if cross[k]:
                        poly.append(cross[k])
                patches.append(poly)
    return segments, patches


def contour(cv, field, box, cell, color, level=1.0, width=3, fill=None, fill_alpha=1.0, alpha=1.0):
    """Draw the `level` outline of `field(px, py)` over `box` (x, y, w, h),
    marching squares `cell` px wide, as a `width` px stroke in `color`, over
    an optional `fill` of the inside. Returns `(segments, patches)` from
    `marching_squares`."""
    segments, patches = marching_squares(field, *box, cell, level)
    c = cv.ctx
    if fill is not None and patches:
        c.new_path()
        for poly in patches:  # one path, one fill: no seams between cells
            c.move_to(*poly[0])
            for p in poly[1:]:
                c.line_to(*p)
            c.close_path()
        c.set_source_rgba(*vb.rgba(fill, fill_alpha))
        c.fill()
    if segments:
        c.new_path()
        for p, q in segments:
            c.move_to(*p)
            c.line_to(*q)
        c.set_source_rgba(*vb.rgba(color, alpha))
        c.set_line_width(width)
        c.set_line_cap(1)   # round caps and joins hide the joints between cells
        c.set_line_join(1)
        c.stroke()
    return segments, patches


def metaballs(balls):
    """A metaball field: the sum of r^2 / d^2 over `balls`, a list of
    (cx, cy, r). Its level 1 outline is a circle of radius r around a lone ball."""
    def field(px, py):
        return sum(r * r / ((px - cx) ** 2 + (py - cy) ** 2 + 1e-6) for cx, cy, r in balls)
    return field


CELL = 20
BOX = (demo.W / 2 - 300, demo.H / 2 - 220, 600, 440)


def draw(n, cv):
    t = n / demo.FPS
    x, y, w, h = BOX
    cx, cy = x + w / 2, y + h / 2
    # Three blobs swing apart and back in, so the outline splits and fuses.
    gap = 0.35 + 0.65 * (0.5 - 0.5 * math.cos(2 * math.pi * t / demo.SECONDS))
    balls = [(cx + 150 * gap * math.cos(a + 0.7 * t), cy + 110 * gap * math.sin(a + 0.7 * t), r)
             for a, r in ((0.3, 62), (2.4, 50), (4.3, 56))]
    field = metaballs(balls)
    for i in range(round(w / CELL) + 1):
        cv.line(x + i * CELL, y, x + i * CELL, y + h, demo.LINE, width=1)
    for j in range(round(h / CELL) + 1):
        cv.line(x, y + j * CELL, x + w, y + j * CELL, demo.LINE, width=1)
    contour(cv, field, BOX, CELL, '#f2c94c', width=3, fill='#2d3354', fill_alpha=0.9)
    for j in range(round(h / CELL) + 1):  # the grid samples that fall inside light up
        for i in range(round(w / CELL) + 1):
            px, py = x + i * CELL, y + j * CELL
            if field(px, py) >= 1:
                demo.dot(cv, px, py, 1.8, color=demo.MUTED, alpha=0.8)
    cv.mark('field', x, y, w, h)


CAPABILITY = Capability(
    id='marching-squares-contour',
    name='Marching squares contour',
    family='particles',
    group='Metaballs & blobs',
    aliases=('marching squares', 'isosurface outline', 'isoline outline', 'metaball contour'),
    definition='A smooth field is sampled on a grid and each cell is cut where the values cross a '
               'threshold, tracing a clean outline around blobs that merge and split as they move.',
    phrasings=('draw an outline around blobby shapes that melt together on a grid',
               'trace the edge of moving metaballs with a crisp line',
               'contour a field so the shapes fuse and pull apart with one outline'),
    related=('isolines-contour-animation', 'koch-snowflake', 'truchet-tiles', 'ink-outline',
             'dot-grid-displacement', 'stroke-draw-on'),
    api=('videobuilder.capabilities.particles.marching_squares_contour.contour',
         'videobuilder.capabilities.particles.marching_squares_contour.marching_squares',
         'videobuilder.capabilities.particles.marching_squares_contour.metaballs'),
    demo=lambda: demo.film(draw),
)
