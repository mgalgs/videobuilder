"""Voronoi relaxation: a clumpy scatter of points, each owning the patch of
the frame nearest to it, slides step by step to the middle of its own patch
until the cells settle into an even, honeycomb-like tiling."""
import math
import random
from functools import lru_cache

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def _clip(poly, ax, ay, nx, ny):
    """`poly` cut by the half-plane (p - a) . n <= 0 (Sutherland-Hodgman)."""
    out = []
    for i, (px, py) in enumerate(poly):
        qx, qy = poly[i - 1]
        dp, dq = (px - ax) * nx + (py - ay) * ny, (qx - ax) * nx + (qy - ay) * ny
        if (dp <= 0) != (dq <= 0):
            k = dq / (dq - dp)
            out.append((qx + (px - qx) * k, qy + (py - qy) * k))
        if dp <= 0:
            out.append((px, py))
    return out


def voronoi_cells(points, box):
    """The Voronoi cell of each of `points` [(x, y), ...] inside `box`
    (x, y, w, h): one convex polygon [(x, y), ...] per point, in order. Each
    cell is the box cut by the bisector against every other point -- quadratic,
    which is fine for the hundred or so points a frame shows."""
    x, y, w, h = box
    rect = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    cells = []
    for i, (px, py) in enumerate(points):
        poly = rect
        for j, (qx, qy) in enumerate(points):
            if j == i or not poly:
                continue
            nx, ny = qx - px, qy - py
            if nx == 0 and ny == 0:
                continue
            poly = _clip(poly, (px + qx) / 2, (py + qy) / 2, nx, ny)
        cells.append(poly)
    return cells


def polygon_area_centroid(poly):
    """(area, (cx, cy)) of a simple polygon; a degenerate one gives its vertex mean."""
    a = cx = cy = 0.0
    for i, (x1, y1) in enumerate(poly):
        x0, y0 = poly[i - 1]
        cr = x0 * y1 - x1 * y0
        a += cr
        cx += (x0 + x1) * cr
        cy += (y0 + y1) * cr
    if abs(a) < 1e-9:
        n = max(len(poly), 1)
        return 0.0, (sum(p[0] for p in poly) / n, sum(p[1] for p in poly) / n)
    return abs(a) / 2, (cx / (3 * a), cy / (3 * a))


def lloyd_steps(points, box, iterations=12):
    """Lloyd's relaxation: `iterations + 1` point sets, the first `points`
    themselves, each next one every point moved to the centroid of its
    Voronoi cell in the one before. Big moves early, ever smaller after, so
    stepping through them reads as a natural settle."""
    steps = [[(float(px), float(py)) for px, py in points]]
    for _ in range(iterations):
        cur = steps[-1]
        nxt = []
        for p, cell in zip(cur, voronoi_cells(cur, box)):
            nxt.append(polygon_area_centroid(cell)[1] if len(cell) >= 3 else p)
        steps.append(nxt)
    return steps


def relaxed_at(steps, p):
    """The points at progress `p` (0 -> 1) through `steps` from `lloyd_steps`,
    gliding linearly between consecutive iterations."""
    f = vb.clamp01(p) * (len(steps) - 1)
    i = min(int(f), len(steps) - 2)
    k = f - i
    return [(ax + (bx - ax) * k, ay + (by - ay) * k) for (ax, ay), (bx, by) in zip(steps[i], steps[i + 1])]


def _mix(a, b, k):
    a, b = vb.canvas.rgba(a), vb.canvas.rgba(b)
    return tuple(round(255 * (u + (v - u) * k)) for u, v in zip(a[:3], b[:3]))


def draw_voronoi(cv, points, box, small, large, edge=None, edge_width=3.0, dot=None, dot_r=5.0):
    """Fill the Voronoi cell of each of `points` inside `box`, coloured from
    `small` to `large` by its area against the average (so uneven cells look
    patchy and a relaxed tiling looks even). `edge` strokes the cell borders,
    `dot` marks the points. Returns the cells."""
    cells = voronoi_cells(points, box)
    areas = [polygon_area_centroid(c)[0] if len(c) >= 3 else 0.0 for c in cells]
    mean = (sum(areas) / len(areas)) if areas else 1.0
    c = cv.ctx
    for cell, area in zip(cells, areas):
        if len(cell) < 3:
            continue
        k = vb.clamp01(0.5 + 0.5 * math.log2(max(area, 1e-6) / mean) / 1.5)
        c.new_path()
        c.move_to(*cell[0])
        for v in cell[1:]:
            c.line_to(*v)
        c.close_path()
        c.set_source_rgba(*vb.canvas.rgba(_mix(small, large, k)))
        c.fill_preserve()
        if edge:
            c.set_source_rgba(*vb.canvas.rgba(edge))
            c.set_line_width(edge_width)
            c.set_line_join(1)  # round
        else:
            c.set_line_width(0.75)  # seal anti-aliasing seams in the cell's own colour
        c.stroke()
    if dot:
        for px, py in points:
            demo.dot(cv, px, py, dot_r, color=dot)
    return cells


BOX = (60, 50, demo.W - 120, demo.H - 100)


@lru_cache(maxsize=1)
def _demo_steps():
    rnd = random.Random(11)
    x, y, w, h = BOX
    pts = []
    # three tight clumps plus a sprinkling: cells start wildly uneven
    for cx, cy, s, n in ((0.28, 0.35, 0.07, 26), (0.7, 0.62, 0.06, 22), (0.55, 0.22, 0.05, 12)):
        pts += [(x + w * vb.clamp01(rnd.gauss(cx, s)), y + h * vb.clamp01(rnd.gauss(cy, s * 1.6)))
                for _ in range(n)]
    pts += [(x + w * rnd.random(), y + h * rnd.random()) for _ in range(10)]
    return lloyd_steps(pts, BOX, iterations=30)


def draw(n, cv):
    pts = relaxed_at(_demo_steps(), demo.phase(n, 0.4, 2.7))
    draw_voronoi(cv, pts, BOX, demo.ACCENT, '#2b3a63', edge=demo.BG, edge_width=4, dot=demo.INK, dot_r=5)
    cv.mark('cells', *BOX)


TECHNIQUE = Technique(
    id='voronoi-relaxation',
    name='Voronoi relaxation',
    family='particles',
    group='Tiling & patterns',
    aliases=("Lloyd's relaxation", "Lloyd's algorithm", 'centroidal Voronoi tessellation', 'Voronoi iteration'),
    definition='Bunched-up points each claim the area closest to them, then keep sliding to the centre '
               'of their own patch until the cells even out into a calm, cell-like tiling.',
    phrasings=('scattered dots that spread themselves out evenly into cells',
               'a cracked-mud cell pattern that smooths out until every cell is about the same size',
               'points push apart and settle like bubbles in a foam'),
    related=('eden-growth', 'worley-cellular-noise', 'lenia', 'pollen-drift', 'diffusion-limited-aggregation',
             'volume-preservation'),
    api=('videobuilder.techniques.particles.voronoi_relaxation.draw_voronoi',
         'videobuilder.techniques.particles.voronoi_relaxation.lloyd_steps',
         'videobuilder.techniques.particles.voronoi_relaxation.relaxed_at',
         'videobuilder.techniques.particles.voronoi_relaxation.voronoi_cells'),
    demo=lambda: demo.film(draw),
)
