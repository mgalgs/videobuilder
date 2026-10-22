"""Voronoi Cells: seed points split a box into polygons, each holding the part
of the plane nearer its own seed than any other; move the seeds and the
borders slide and re-form between them."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def _clip(poly, ax, ay, bx, by):
    """`poly` cut down to the half-plane nearer (ax, ay) than (bx, by)."""
    mx, my, nx, ny = (ax + bx) / 2, (ay + by) / 2, bx - ax, by - ay
    side = [(x - mx) * nx + (y - my) * ny for x, y in poly]  # <= 0: on a's side of the bisector
    out = []
    for i, (p, s) in enumerate(zip(poly, side)):
        q, t = poly[i - 1], side[i - 1]
        if (s <= 0) != (t <= 0):
            k = t / (t - s)
            out.append((q[0] + (p[0] - q[0]) * k, q[1] + (p[1] - q[1]) * k))
        if s <= 0:
            out.append(p)
    return out


def voronoi_cells(seeds, x, y, w, h):
    """The Voronoi cell of each of `seeds` [(x, y), ...] inside the box
    (x, y, w, h): a list of polygons [(x, y), ...], one per seed in order
    (empty for a seed outside the box or sharing a spot with another). Each
    is the box clipped by the bisector to every other seed; fine for the few
    dozen seeds a frame shows, recomputed every frame as they move."""
    box = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    cells = []
    for i, (ax, ay) in enumerate(seeds):
        poly = box
        # nearest first: the cell shrinks fast and later cuts touch few vertices
        for bx, by in sorted((s for j, s in enumerate(seeds) if j != i),
                             key=lambda s: (s[0] - ax) ** 2 + (s[1] - ay) ** 2):
            if (bx, by) == (ax, ay):
                poly = []
            if not poly:
                break
            poly = _clip(poly, ax, ay, bx, by)
        cells.append(poly)
    return cells


def wandering_seeds(x, y, w, h, count, t, speed=1.0, seed=0):
    """`count` seed points scattered over the box (x, y, w, h), each drifting
    on its own slow loop at time `t` seconds and staying inside the box."""
    rnd = random.Random(seed)
    cols = max(1, round(math.sqrt(count * w / h)))
    rows = math.ceil(count / cols)
    cw, ch = w / cols, h / rows
    out = []
    for i in range(count):
        r, c = divmod(i, cols)
        hx, hy = x + (c + rnd.uniform(0.25, 0.75)) * cw, y + (r + rnd.uniform(0.25, 0.75)) * ch
        fx, fy, ph = rnd.uniform(0.5, 1.0), rnd.uniform(0.5, 1.0), rnd.uniform(0, 2 * math.pi)
        px = hx + 0.45 * cw * math.sin(t * speed * fx + ph)
        py = hy + 0.45 * ch * math.cos(t * speed * fy + ph * 1.3)
        out.append((min(max(px, x + 1), x + w - 1), min(max(py, y + 1), y + h - 1)))
    return out


def _path(ctx, poly):
    ctx.new_path()
    ctx.move_to(*poly[0])
    for p in poly[1:]:
        ctx.line_to(*p)
    ctx.close_path()


def draw_cells(cv, seeds, x, y, w, h, colors, edge=None, edge_width=2.0, dot=None, dot_r=5.0, grow=None,
               highlight=None, highlight_color=demo.ACCENT):
    """Draw the Voronoi diagram of `seeds` in the box (x, y, w, h): each cell
    filled with `colors[i % len(colors)]`, its border stroked in `edge` and its
    seed marked with a `dot`. `grow` (a radius) shows each cell only within
    that distance of its seed, so cells swell out from their seeds and meet
    along the borders. Cell number `highlight` is filled `highlight_color`.
    Returns the cells."""
    cells = voronoi_cells(seeds, x, y, w, h)
    c = cv.ctx
    for i, (poly, (sx, sy)) in enumerate(zip(cells, seeds)):
        if len(poly) < 3:
            continue
        color = highlight_color if i == highlight else colors[i % len(colors)]
        c.save()
        _path(c, poly)
        c.clip()  # strokes below show only their inner half, so the neighbour's half completes each border
        if grow is not None:
            c.arc(sx, sy, max(grow, 0.0), 0, 2 * math.pi)
            c.clip()
        c.set_source_rgba(*vb.canvas.rgba(color))
        c.paint()
        if edge:
            c.set_source_rgba(*vb.canvas.rgba(edge))
            c.set_line_width(edge_width * 2)
            _path(c, poly)
            if grow is not None:
                c.new_sub_path()
                c.arc(sx, sy, max(grow, 0.0), 0, 2 * math.pi)  # the growing front, until it reaches the borders
            c.stroke()
        c.restore()
    if dot:
        for i, (sx, sy) in enumerate(seeds):
            demo.dot(cv, sx, sy, dot_r * (1.4 if i == highlight else 1.0),
                     color=demo.INK if i == highlight else dot)
    return cells


PALETTE = ('#1d2135', '#262c48', '#30375a', '#3a426c')


def draw(n, cv):
    t = n / demo.FPS
    x, y, w, h = 0, 0, demo.W, demo.H
    seeds = wandering_seeds(x, y, w, h, 28, t, speed=1.3, seed=11)
    grow = 0.3 * demo.W * demo.phase(n, 0.1, 1.3)  # cells swell at one speed from their seeds and meet on the borders
    draw_cells(cv, seeds, x, y, w, h, PALETTE, edge='#8f9cff', edge_width=2.5, dot=demo.MUTED, grow=grow,
               highlight=10)
    cv.mark('cells', x, y, w, h)


TECHNIQUE = Technique(
    id='voronoi-cells',
    name='Voronoi cells',
    family='particles',
    group='Tiling & patterns',
    aliases=('Voronoi diagram', 'nearest-seed regions', 'Voronoi cell drift', 'cell pattern drift'),
    definition='Scattered points each claim the patch of space closer to them than to any other point, '
               'tiling the frame with polygons whose borders shift as the points wander.',
    phrasings=('a cracked-mud cell pattern where the cells shift as their dots move',
               'split the screen into polygon cells around moving points',
               'organic cell tiles that grow out from dots and meet at the edges'),
    related=('worley-cellular-noise', 'eden-growth', 'streamgraph-flow', 'smoke-simulation',
             'area-fill-sweep', 'connector-network'),
    api=('videobuilder.techniques.particles.voronoi_cells.draw_cells',
         'videobuilder.techniques.particles.voronoi_cells.voronoi_cells',
         'videobuilder.techniques.particles.voronoi_cells.wandering_seeds'),
    demo=lambda: demo.film(draw),
)
