"""Worley Cellular Noise: scatter feature points, then shade every spot by its
distance to the nearest one, so the plane breaks into rounded cells that are
bright at their seeds and dark along the creases where two cells meet --
cracked stone, scales, foam. Move the points and the cells reshape."""
import math
import random

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ...canvas import rgba


def worley_f1(x, y, points):
    """The F1 Worley value at (x, y): the distance to the nearest of
    `points` (a sequence of (x, y)). Read it anywhere a scalar noise is
    wanted; `worley_cells` draws the same field fast."""
    return min(math.hypot(x - px, y - py) for px, py in points)


def jittered_points(cols, rows, x, y, w, h, jitter=0.8, seed=0):
    """Feature points for cellular noise: one per cell of a `cols` x `rows`
    grid over the box, each pushed off its cell centre by up to `jitter`
    half-cells, so the cells come out even in size but irregular in shape."""
    rnd = random.Random(f'worley:{seed}')
    cw, ch = w / cols, h / rows
    return [(x + (i + 0.5 + rnd.uniform(-0.5, 0.5) * jitter) * cw,
             y + (j + 0.5 + rnd.uniform(-0.5, 0.5) * jitter) * ch)
            for j in range(rows) for i in range(cols)]


def _clip(poly, ax, ay, nx, ny):
    """`poly` cut to the half-plane where (p - a) . n <= 0."""
    out = []
    for k, (px, py) in enumerate(poly):
        qx, qy = poly[k - 1]
        dp = (px - ax) * nx + (py - ay) * ny
        dq = (qx - ax) * nx + (qy - ay) * ny
        if (dp <= 0) != (dq <= 0):
            t = dq / (dq - dp)
            out.append((qx + (px - qx) * t, qy + (py - qy) * t))
        if dp <= 0:
            out.append((px, py))
    return out


def voronoi_polygons(points, x, y, w, h):
    """Each point's cell inside the box: the polygon of places nearer to it
    than to any other point (the region where it is the F1 winner). Returns
    one list of (x, y) corners per point, in order (empty if off the box)."""
    box = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    cells = []
    for i, (ax, ay) in enumerate(points):
        poly = box
        for j, (bx, by) in enumerate(points):
            if i != j and poly:
                poly = _clip(poly, (ax + bx) / 2, (ay + by) / 2, bx - ax, by - ay)
        cells.append(poly)
    return cells


def worley_cells(cv, points, x, y, w, h, reach, near=demo.TEAL, far=demo.BG, crack=None,
                 crack_width=3.0, seeds=None, seed_radius=4.0):
    """Draw F1 cellular noise over the box: every pixel coloured by its
    distance to the nearest of `points`, from `near` at a point to `far` at
    `reach` px and beyond. Each cell is filled with a radial gradient about
    its own point, clipped to its Voronoi polygon -- exactly the F1 field,
    at vector sharpness. `crack`: a colour to line the cell borders in
    (None: the creases show only as the dark valleys); `seeds`: a colour to
    dot each feature point in. Animate by moving `points` between frames."""
    c = cv.ctx
    n0, f0 = rgba(near), rgba(far)
    cells = voronoi_polygons(points, x, y, w, h)
    for (px, py), poly in zip(points, cells):
        if len(poly) < 3:
            continue
        g = cairo.RadialGradient(px, py, 0, px, py, reach)
        g.add_color_stop_rgba(0, *n0)
        g.add_color_stop_rgba(1, *f0)
        c.save()
        c.move_to(*poly[0])
        for q in poly[1:]:
            c.line_to(*q)
        c.close_path()
        c.set_source(g)
        c.fill_preserve()
        if crack:
            c.set_source_rgba(*rgba(crack))
            c.set_line_width(crack_width)
            c.set_line_join(cairo.LINE_JOIN_ROUND)
            c.stroke()
        else:
            c.new_path()
        c.restore()
    if seeds:
        for px, py in points:
            demo.dot(cv, px, py, seed_radius, color=seeds)
    return cells


COLS, ROWS = 8, 5
PAD = 60


def draw(n, cv):
    x, y, w, h = PAD, PAD, demo.W - 2 * PAD, demo.H - 2 * PAD
    rnd = random.Random('worley-demo')
    base = jittered_points(COLS + 2, ROWS + 2, x - w / COLS, y - h / ROWS, w * (COLS + 2) / COLS,
                           h * (ROWS + 2) / ROWS, jitter=0.7, seed=3)   # a ring of points past the edge too
    drift = vb.ease_in_out_quart(demo.phase(n, 0.1, 2.9))
    points = []
    for bx, by in base:
        a, s, r = rnd.uniform(0, 2 * math.pi), rnd.choice((-1, 1)), rnd.uniform(25, 45)
        ang = a + s * 2 * math.pi * drift
        points.append((bx + r * (math.cos(ang) - math.cos(a)), by + r * (math.sin(ang) - math.sin(a))))
    with cv.clip(x, y, w, h, radius=24):
        worley_cells(cv, points, x - 200, y - 200, w + 400, h + 400, reach=125, near='#8fe3d4',
                     far='#0d1d22', crack='#081013', crack_width=3, seeds=demo.ACCENT)
    cv.mark('field', x, y, w, h)


CAPABILITY = Capability(
    id='worley-cellular-noise',
    name='Worley cellular noise',
    family='particles',
    group='Noise & fields',
    aliases=('Worley noise', 'Voronoi noise', 'cell noise', 'cellular noise', 'F1 noise'),
    definition='A pattern of rounded cells, each glowing at a scattered seed point and darkening toward '
               'the seams where it meets its neighbours, like cracked stone or foam.',
    phrasings=('fill the background with a shifting cracked-stone cell pattern',
               'make an organic cell texture where the cells slowly squeeze and reshape',
               'give me that bubbly, scaly Voronoi-looking noise'),
    related=('noise-vertex-wobble', 'voronoi-cells', 'voronoi-relaxation', 'noise-field-warp', 'wobble',
             'wiggle-path'),
    api=('videobuilder.capabilities.particles.worley_cellular_noise.worley_cells',
         'videobuilder.capabilities.particles.worley_cellular_noise.voronoi_polygons',
         'videobuilder.capabilities.particles.worley_cellular_noise.jittered_points',
         'videobuilder.capabilities.particles.worley_cellular_noise.worley_f1'),
    demo=lambda: demo.film(draw),
)
