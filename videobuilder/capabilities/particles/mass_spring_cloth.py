"""Mass-spring cloth: a sheet made of a grid of point masses, each tied to
its neighbours by springs, so it sags under gravity, drapes from the points
it is pinned at, ripples in the wind and swings free when a pin lets go."""
import math
from functools import lru_cache

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def cloth_sheet(x, y, w, h, frames, fps=30, cols=20, rows=14, tilt=90.0, pins=None, releases=(), gravity=1400.0,
                wind=(0.0, 0.0, 0.0), gust=0.0, stiffness=1.0, bend=0.3, give=0.3, damping=0.01, iterations=6,
                substeps=3):
    """Simulate a `w` x `h` sheet as a `cols` x `rows` grid of masses in 3D
    (x right, y down, z away from the viewer). Its top edge starts along y
    = `y` from x = `x` to `x + w`, and the sheet starts tilted `tilt`
    degrees back from hanging straight down (90: lying flat, pointing away).
    Returns one grid per frame for `frames` frames at `fps`: a tuple of
    `rows` rows, each a tuple of `cols` (x, y, z); `draw_cloth` draws one.

    Each mass is sprung to its right and lower neighbours (structure), its
    diagonals (shear) and the masses two along (`bend`, 0 = limp silk, 1 =
    stiff card). `stiffness` 0..1 is how firmly springs resist stretching
    and `give` 0..1 how hard they push back when squeezed (low lets the
    sheet buckle into folds). `pins` lists the (col, row) masses held in
    place (default: the two top corners); `releases` is a tuple of
    ((col, row), seconds) pins let go of at that time. `wind` is a steady
    (x, y, z) push in px/s^2 and `gust` adds a rolling flutter through the
    sheet. Pure: same arguments, same grids, so a `draw(n, cv)` can index
    it by frame."""
    if pins is None:
        pins = ((0, 0), (cols - 1, 0))
    return _simulate(float(x), float(y), float(w), float(h), int(frames), float(fps), int(cols), int(rows),
                     float(tilt), tuple((int(c), int(r)) for c, r in pins),
                     tuple(((int(c), int(r)), float(s)) for (c, r), s in releases), float(gravity),
                     tuple(float(v) for v in wind), float(gust), float(stiffness), float(bend), float(give),
                     float(damping), int(iterations), int(substeps))


@lru_cache(maxsize=16)
def _simulate(x0, y0, w, h, frames, fps, cols, rows, tilt, pins, releases, gravity, wind, gust, stiffness, bend,
              give, damping, iterations, substeps):
    idx = lambda c, r: r * cols + c  # noqa: E731
    n = cols * rows
    tc, ts = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
    px = [x0 + w * (i % cols) / (cols - 1) for i in range(n)]
    py = [y0 + h * (i // cols) / (rows - 1) * tc for i in range(n)]
    pz = [h * (i // cols) / (rows - 1) * ts for i in range(n)]
    ox, oy, oz = px[:], py[:], pz[:]  # previous positions (Verlet)
    springs = []
    for r in range(rows):
        for c in range(cols):
            for dc, dr, k in ((1, 0, 1.0), (0, 1, 1.0), (1, 1, 0.5), (-1, 1, 0.5), (2, 0, bend), (0, 2, bend)):
                cc, rr = c + dc, r + dr
                if 0 <= cc < cols and rr < rows and k > 0:
                    a, b = idx(c, r), idx(cc, rr)
                    rest = math.dist((px[a], py[a], pz[a]), (px[b], py[b], pz[b]))
                    springs.append((a, b, rest, k * stiffness))
    pinned = {idx(c, r): (px[idx(c, r)], py[idx(c, r)], pz[idx(c, r)]) for c, r in pins}
    dt2 = (1.0 / fps / substeps) ** 2
    out = []
    for f in range(frames):
        out.append(tuple(tuple((px[idx(c, r)], py[idx(c, r)], pz[idx(c, r)]) for c in range(cols))
                         for r in range(rows)))
        for (c, r), at in releases:
            if f / fps >= at:
                pinned.pop(idx(c, r), None)
        for s in range(substeps):
            t = (f + s / substeps) / fps
            for i in range(n):
                if i in pinned:
                    continue
                c, r = i % cols, i // cols
                # Flutter: a wave rolling through the sheet, stronger away from the top edge.
                fl = gust * math.sin(t * 9.0 - 0.45 * c - 0.6 * r) * r / rows
                vx, vy, vz = ((px[i] - ox[i]) * (1 - damping), (py[i] - oy[i]) * (1 - damping),
                              (pz[i] - oz[i]) * (1 - damping))
                ox[i], oy[i], oz[i] = px[i], py[i], pz[i]
                px[i] += vx + wind[0] * dt2
                py[i] += vy + (wind[1] + gravity) * dt2
                pz[i] += vz + (wind[2] + fl) * dt2
            for _ in range(iterations):
                for a, b, rest, k in springs:
                    dx, dy, dz = px[b] - px[a], py[b] - py[a], pz[b] - pz[a]
                    d = math.sqrt(dx * dx + dy * dy + dz * dz) or 1e-6
                    corr = k * 0.5 * (d - rest) / d * (1.0 if d > rest else give)
                    wa, wb = a not in pinned, b not in pinned
                    if wa and wb:
                        px[a] += dx * corr; py[a] += dy * corr; pz[a] += dz * corr
                        px[b] -= dx * corr; py[b] -= dy * corr; pz[b] -= dz * corr
                    elif wa:
                        px[a] += 2 * dx * corr; py[a] += 2 * dy * corr; pz[a] += 2 * dz * corr
                    elif wb:
                        px[b] -= 2 * dx * corr; py[b] -= 2 * dy * corr; pz[b] -= 2 * dz * corr
                for i, (qx, qy, qz) in pinned.items():
                    px[i], py[i], pz[i] = qx, qy, qz
    return tuple(out)


def project(p, cx=demo.W / 2, cy=demo.H / 2, distance=1800.0):
    """A `cloth_sheet` point (x, y, z) -> screen (x, y), in perspective from
    `distance` px in front of the z = 0 plane, centred on (cx, cy)."""
    k = distance / (distance + p[2])
    return cx + (p[0] - cx) * k, cy + (p[1] - cy) * k


def _rgb(color):
    return vb.canvas.rgba(color)[:3]


def draw_cloth(cv, grid, color=demo.ACCENT, back=None, shade='#000000', lines=None, alpha=1.0, width=1.0,
               distance=1800.0):
    """Draw one `cloth_sheet` frame onto `cv` in perspective (see `project`):
    each grid cell filled in `color` (`back` for cells showing their reverse
    side, default `color`), darkened towards `shade` the more it turns away
    from a light above and in front, so folds and ripples read. `lines` (a
    color) traces the springs. Far cells are drawn first."""
    rows, cols = len(grid), len(grid[0])
    c = cv.ctx
    front, rear, dark = _rgb(color), _rgb(back or color), _rgb(shade)
    light = (-0.3, -0.5, -0.81)  # towards the light: up-left, in front
    cells = []
    for r in range(rows - 1):
        for k in range(cols - 1):
            a, b, d, e = grid[r][k], grid[r][k + 1], grid[r + 1][k + 1], grid[r + 1][k]
            ux, uy, uz = d[0] - a[0], d[1] - a[1], d[2] - a[2]
            vx, vy, vz = e[0] - b[0], e[1] - b[1], e[2] - b[2]
            nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
            ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1e-6
            dot = (nx * light[0] + ny * light[1] + nz * light[2]) / ln
            facing = nz < 0  # normal points at the viewer: the front side shows
            lit = abs(dot)
            base = front if facing else rear
            m = 0.2 + 0.8 * lit ** 1.5
            rgb = tuple(dark[i] + (base[i] - dark[i]) * m for i in range(3))
            cells.append(((a[2] + b[2] + d[2] + e[2]) / 4, [project(p, distance=distance) for p in (a, b, d, e)], rgb))
    cells.sort(key=lambda cell: -cell[0])
    for _, q, rgb in cells:
        c.new_path()
        c.move_to(*q[0])
        for p in q[1:]:
            c.line_to(*p)
        c.close_path()
        c.set_source_rgba(*rgb, alpha)
        c.fill_preserve()
        c.set_line_width(0.8)  # seal hairline gaps between neighbouring cells
        c.stroke()
        if lines:
            c.new_path()
            c.move_to(*q[3])
            c.line_to(*q[0])
            c.line_to(*q[1])
            c.set_source_rgba(*vb.canvas.rgba(lines, 0.25 * alpha))
            c.set_line_width(width)
            c.stroke()
    pts = [project(p, distance=distance) for row in grid for p in row]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    cv.mark('cloth', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


COLS, ROWS = 20, 14
SHEET_W, SHEET_H = 440, 290
LEFT, TOP = demo.W / 2 - SHEET_W / 2, 90
RELEASE = 2.2


def _grids():
    # Lying flat and pinned by its two top corners, the sheet falls, swings down and flutters;
    # late on the right corner lets go.
    return cloth_sheet(LEFT, TOP, SHEET_W, SHEET_H, round(demo.SECONDS * demo.FPS), demo.FPS, COLS, ROWS,
                       tilt=80.0, gravity=900.0, releases=(((COLS - 1, 0), RELEASE),), wind=(0.0, 0.0, -160.0),
                       gust=700.0)


def draw(n, cv):
    grid = _grids()[n]
    draw_cloth(cv, grid, color=demo.TEAL, back='#2f8f80', lines=demo.INK)
    for k in (0, COLS - 1):
        if k == 0 or n / demo.FPS < RELEASE:
            demo.dot(cv, *project(grid[0][k]), r=10, color=demo.ACCENT)


TECHNIQUE = Technique(
    id='mass-spring-cloth',
    name='Mass-spring cloth',
    family='particles',
    group='Soft bodies & cloth',
    aliases=('cloth simulation', 'verlet cloth', 'spring mesh', 'fabric simulation', 'flag wave'),
    definition='A sheet built from a grid of small weights joined by springs, so it sags, drapes, '
               'flutters in the wind and swings loose when one of its pins is released.',
    phrasings=('a piece of fabric hanging from pins that sways in the breeze',
               'make a cloth that drops and swings when one corner comes loose',
               'a flag or curtain made of a stretchy grid that ripples'),
    related=('spring-motion', 'spring-return', 'falling-sand', 'soft-body-jelly', 'line-weave',
             'overdamped-spring'),
    api=('videobuilder.techniques.particles.mass_spring_cloth.cloth_sheet',
         'videobuilder.techniques.particles.mass_spring_cloth.draw_cloth'),
    demo=lambda: demo.film(draw),
)
