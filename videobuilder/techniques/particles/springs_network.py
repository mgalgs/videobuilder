"""Springs Network: a grid of point masses, each tied to its neighbours by
springs and pinned at the corners, so a jab at one node sends a wave of
stretching and squeezing through the whole mesh before it rings down."""
import math
from functools import lru_cache

from .. import _demo as demo
from ..schema import Technique


def spring_lattice(x, y, w, h, frames, fps=30, cols=11, rows=7, pokes=(), pinned='corners',
                   stiffness=500.0, shear=150.0, damping=1.0, spread=1.0, substeps=8):
    """Simulate a `cols` x `rows` mass-spring lattice laid out over the box
    (x, y, w, h). Returns one frame per entry for `frames` frames at `fps`:
    a tuple of rows, each a tuple of (x, y) node positions.

    Every node is sprung to its right and lower neighbours (`stiffness`) and
    to its diagonal neighbours (`shear`, which keeps the cells from
    collapsing). `pokes` is a sequence of (seconds, col, row, vx, vy): at that
    time the node gets a kick of (vx, vy) px/s, and nodes around it a share
    that falls off over `spread` cells (0 kicks only the one node). `pinned` is 'corners',
    'edges' (the whole border is fixed, like a drumhead) or a sequence of
    (col, row) nodes. Lower `damping` rings longer. The result is pure, so a
    `draw(n, cv)` can index it by frame."""
    if pinned == 'corners':
        pins = ((0, 0), (cols - 1, 0), (0, rows - 1), (cols - 1, rows - 1))
    elif pinned == 'edges':
        pins = tuple((c, r) for r in range(rows) for c in range(cols) if c in (0, cols - 1) or r in (0, rows - 1))
    else:
        pins = tuple(tuple(p) for p in pinned)
    pokes = tuple((float(t), int(c), int(r), float(vx), float(vy)) for t, c, r, vx, vy in pokes)
    return _simulate(float(x), float(y), float(w), float(h), int(frames), float(fps), int(cols), int(rows), pokes,
                     pins, float(stiffness), float(shear), float(damping), float(spread), int(substeps))


@lru_cache(maxsize=32)
def _simulate(x, y, w, h, frames, fps, cols, rows, pokes, pins, k, ks, damping, spread, substeps):
    idx = lambda c, r: r * cols + c  # noqa: E731
    n = cols * rows
    px = [x + w * (i % cols) / (cols - 1) for i in range(n)]
    py = [y + h * (i // cols) / (rows - 1) for i in range(n)]
    ux, uy = [0.0] * n, [0.0] * n
    fixed = {idx(c, r) for c, r in pins}
    springs = []
    for r in range(rows):
        for c in range(cols):
            for dc, dr, stiff in ((1, 0, k), (0, 1, k), (1, 1, ks), (-1, 1, ks)):
                if 0 <= c + dc < cols and r + dr < rows:
                    a, b = idx(c, r), idx(c + dc, r + dr)
                    springs.append((a, b, math.hypot(px[b] - px[a], py[b] - py[a]), stiff))
    kicks = {}
    for t, c0, r0, vx, vy in pokes:
        for r in range(rows):
            for c in range(cols):
                d2 = (c - c0) ** 2 + (r - r0) ** 2
                share = math.exp(-d2 / (2 * spread * spread)) if spread else float(d2 == 0)
                if share > 0.02:
                    kicks.setdefault(round(t * fps), []).append((idx(c, r), vx * share, vy * share))
    dt = 1.0 / fps / substeps
    out = []
    for f in range(frames):
        for i, vx, vy in kicks.get(f, ()):
            if i not in fixed:
                ux[i] += vx
                uy[i] += vy
        out.append(tuple(tuple(zip(px[r * cols:(r + 1) * cols], py[r * cols:(r + 1) * cols])) for r in range(rows)))
        for _ in range(substeps):
            fx, fy = [0.0] * n, [0.0] * n
            for a, b, rest, stiff in springs:
                dx, dy = px[b] - px[a], py[b] - py[a]
                d = math.hypot(dx, dy) or 1e-6
                nx, ny = dx / d, dy / d
                rel = (ux[b] - ux[a]) * nx + (uy[b] - uy[a]) * ny
                s = stiff * (d - rest) + damping * 4 * rel
                fx[a] += s * nx; fy[a] += s * ny
                fx[b] -= s * nx; fy[b] -= s * ny
            for i in range(n):
                if i in fixed:
                    continue
                ux[i] = (ux[i] + fx[i] * dt) * (1 - 0.004 * damping)
                uy[i] = (uy[i] + fy[i] * dt) * (1 - 0.004 * damping)
                px[i] += ux[i] * dt
                py[i] += uy[i] * dt
    return tuple(out)


def draw_lattice(cv, grid, color=demo.TEAL, node=demo.INK, width=2.0, alpha=1.0, braces=0.18, pins=()):
    """Draw a lattice frame (as `spring_lattice` returns): the springs as
    lines (diagonal braces faint, at `braces` alpha; 0 hides them), a small
    dot per mass, and a larger ring on each (col, row) in `pins`."""
    rows, cols = len(grid), len(grid[0])
    if braces:
        for r in range(rows - 1):
            for c in range(cols - 1):
                (ax, ay), (bx, by) = grid[r][c], grid[r + 1][c + 1]
                cv.line(ax, ay, bx, by, color, width=width * 0.5, alpha=alpha * braces)
                (ax, ay), (bx, by) = grid[r][c + 1], grid[r + 1][c]
                cv.line(ax, ay, bx, by, color, width=width * 0.5, alpha=alpha * braces)
    for r in range(rows):
        for c in range(cols):
            x0, y0 = grid[r][c]
            if c + 1 < cols:
                cv.line(x0, y0, *grid[r][c + 1], color, width=width, alpha=alpha)
            if r + 1 < rows:
                cv.line(x0, y0, *grid[r + 1][c], color, width=width, alpha=alpha)
    for row in grid:
        for x0, y0 in row:
            demo.dot(cv, x0, y0, width * 1.6, color=node, alpha=alpha)
    for c, r in pins:
        demo.dot(cv, *grid[r][c], width * 4, color=node, alpha=alpha)
        demo.dot(cv, *grid[r][c], width * 2.4, color=demo.BG, alpha=alpha)
    xs = [p[0] for row in grid for p in row]
    ys = [p[1] for row in grid for p in row]
    cv.mark('lattice', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


COLS, ROWS = 12, 8
BOX = (demo.W / 2 - 280, demo.H / 2 - 180, 560, 360)
POKES = ((0.4, 4, 3, 420.0, -340.0), (1.5, 8, 5, -380.0, 320.0))  # (s, col, row, vx, vy)
PINS = ((0, 0), (COLS - 1, 0), (0, ROWS - 1), (COLS - 1, ROWS - 1))


def draw(n, cv):
    frames = spring_lattice(*BOX, round(demo.SECONDS * demo.FPS), demo.FPS, COLS, ROWS, POKES, damping=0.5, spread=1.3)
    grid = frames[n]
    draw_lattice(cv, grid, pins=PINS)
    for t, c, r, _, _ in POKES:  # the struck node flashes the accent colour, then fades back
        glow = 1 - demo.phase(n, t, t + 0.9)
        if n / demo.FPS >= t and glow > 0:
            demo.dot(cv, *grid[r][c], 6 + 12 * glow, color=demo.ACCENT, alpha=0.4 + 0.6 * glow)


TECHNIQUE = Technique(
    id='springs-network',
    name='Springs network',
    family='particles',
    group='Soft bodies & cloth',
    aliases=('mass-spring lattice', 'spring grid', 'spring mesh'),
    definition='A mesh of dots joined by springy links, where knocking one dot sends a ripple of stretching '
               'and squashing through the whole net until it wobbles back into shape.',
    phrasings=('a grid of points connected by springs that jiggles when you poke it',
               'show a stretchy net that ripples out from where it gets hit',
               'a wobbly elastic mesh that shakes and then settles'),
    related=('spring-motion', 'spring-return', 'small-multiples-cascade', 'critically-damped-spring',
             'overdamped-spring', 'force-directed-network-settle'),
    api=('videobuilder.techniques.particles.springs_network.spring_lattice',
         'videobuilder.techniques.particles.springs_network.draw_lattice'),
    demo=lambda: demo.film(draw),
)
