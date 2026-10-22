"""Dam break: a tall block of water held at one end of a tank is let go; it
slumps, races along the floor as a thin surge, slams into the far wall and
throws up a splash, then sloshes back and settles.

The water is a small particle fluid (double-density relaxation), simulated
once in tank units and cached, so any frame can be drawn in any order."""
import functools
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

WATER = '#4fa3e0'


@functools.lru_cache(maxsize=8)
def simulate(seconds=3.0, fps=30, aspect=2.0, column=0.4, depth=0.8, spacing=0.024, release=0.0,
             gravity=9.0, substeps=4, stiffness=30.0, seed=0):
    """A dam break in a tank `aspect` wide by 1 high (y = 0 is the floor):
    a block `column` wide and `depth` high of particles `spacing` apart starts
    against the left wall, is settled still behind a gate, and is let go at `release` seconds. Returns one
    tuple per frame (`seconds * fps` of them) of the particles' `(x, y, speed)`
    in tank units. Deterministic for a given `seed`; cached, so call freely."""
    rnd = random.Random(f'dam-break:{seed}')
    h = spacing * 2.2                       # interaction radius
    k, k_near = stiffness, stiffness * 10                  # pressure and near-pressure stiffness
    rest = sum((1 - math.hypot(i, j) * spacing / h) ** 2   # the starting lattice's own density
               for i in range(-3, 4) for j in range(-3, 4) if 0 < math.hypot(i, j) * spacing < h)
    pts = []
    nx, ny = max(1, int(column / spacing)), max(1, int(depth / spacing))
    for j in range(ny):
        for i in range(nx):
            pts.append([spacing * (i + 0.5) + rnd.uniform(-1e-3, 1e-3), spacing * (j + 0.5), 0.0, 0.0])
    dt = 1.0 / (fps * substeps)
    frames = []
    settle = round(0.6 * fps)               # frames run before the first, gate shut, to let the block settle
    for n in range(-settle, round(seconds * fps)):
        for _ in range(substeps):
            held = n / fps < release
            for p in pts:
                p[3] -= gravity * dt
                p.append(p[0])
                p.append(p[1])
                p[0] += p[2] * dt
                p[1] += p[3] * dt
            grid = {}
            for idx, p in enumerate(pts):
                grid.setdefault((int(p[0] // h), int(p[1] // h)), []).append(idx)
            for idx, p in enumerate(pts):
                gx, gy = int(p[0] // h), int(p[1] // h)
                near = []
                rho = rho_n = 0.0
                for ox in (-1, 0, 1):
                    for oy in (-1, 0, 1):
                        for jdx in grid.get((gx + ox, gy + oy), ()):
                            if jdx == idx:
                                continue
                            q = pts[jdx]
                            dx, dy = q[0] - p[0], q[1] - p[1]
                            d2 = dx * dx + dy * dy
                            if d2 < h * h:
                                r = math.sqrt(d2) or 1e-9
                                a = 1 - r / h
                                rho += a * a
                                rho_n += a * a * a
                                near.append((q, dx / r, dy / r, a))
                press, press_n = k * (rho - rest), k_near * rho_n
                sx = sy = 0.0
                for q, ux, uy, a in near:
                    m = dt * dt * (press * a + press_n * a * a) * 0.5
                    q[0] += ux * m
                    q[1] += uy * m
                    sx -= ux * m
                    sy -= uy * m
                p[0] += sx
                p[1] += sy
            right = column if held else aspect
            for p in pts:
                r = spacing * 0.5
                if p[0] < r:
                    p[0] = r
                if p[0] > right - r:
                    p[0] = right - r
                if p[1] < r:
                    p[1] = r
                if p[1] > 1.6:              # the splash may leave the tank's rim, but not the frame
                    p[1] = 1.6
                px, py = p.pop(-2), p.pop(-1)
                p[2], p[3] = (p[0] - px) / dt, (p[1] - py) / dt
                v = math.hypot(p[2], p[3])
                cap = 0.0 if n < 0 else 1.6 * math.sqrt(gravity * depth)   # a wall clamp can't fling a drop
                if v > cap:
                    p[2], p[3] = (p[2] * cap / v, p[3] * cap / v) if v else (0.0, 0.0)
        if n >= 0:
            frames.append(tuple((p[0], p[1], math.hypot(p[2], p[3])) for p in pts))
    return tuple(frames)


def _mix(a, b, u):
    a, b = vb.canvas.rgba(a), vb.canvas.rgba(b)
    return tuple(x + (y - x) * u for x, y in zip(a[:3], b[:3]))


def draw_dam_break(cv, x, y, w, t, sim=None, color=WATER, foam='#eaf6ff', radius=None, fps=30, **kw):
    """Draw the water of a dam break `t` seconds in, in a tank whose floor
    starts at (x, y) and runs `w` px to the right (the tank is `w / aspect`
    high, above the floor). `sim` is a `simulate()` result (made from `kw`
    if not given). Each particle is a dot shaded from `color` when still to
    `foam` when fast, so the surge front and the splash read white. Draws
    only the water: the tank, walls and any gate are the caller's."""
    sim = sim if sim is not None else simulate(fps=fps, **kw)
    aspect = kw.get('aspect', 2.0)
    s = w / aspect
    n = max(0, min(len(sim) - 1, int(t * fps)))
    r = radius if radius is not None else s * kw.get('spacing', 0.024) * 0.62
    c = cv.ctx
    for px, py, speed in sorted(sim[n], key=lambda q: q[2]):   # fast foam on top
        c.set_source_rgb(*_mix(color, foam, vb.clamp01((speed - 1.6) / 2.4)))
        c.new_path()
        c.arc(x + px * s, y - py * s, r, 0, 2 * math.pi)
        c.fill()


TANK_W = 760
SIM = dict(release=0.35)


def draw(n, cv):
    t = n / demo.FPS
    x0, floor_y = (demo.W - TANK_W) / 2, demo.H - 70
    tall = TANK_W / 2.0
    sim = simulate(**SIM)
    draw_dam_break(cv, x0, floor_y, TANK_W, t, sim)
    wall = 6
    for xx in (x0 - wall / 2, x0 + TANK_W + wall / 2):
        cv.line(xx, floor_y + wall / 2, xx, floor_y - tall, demo.MUTED, width=wall)
    cv.line(x0 - wall, floor_y + wall / 2, x0 + TANK_W + wall, floor_y + wall / 2, demo.MUTED, width=wall)
    lift = vb.ease_in_expo(demo.phase(n, SIM['release'] - 0.05, SIM['release'] + 0.35))
    gx = x0 + 0.4 * tall + 4
    gate_h = 0.86 * tall
    cv.rect(gx, floor_y - gate_h - lift * (gate_h + 200), 12, gate_h, demo.ACCENT, radius=3,
            alpha=1 - demo.phase(n, SIM['release'] + 0.2, SIM['release'] + 0.45))
    cv.mark('tank', x0, floor_y - tall, TANK_W, tall)


TECHNIQUE = Technique(
    id='dam-break',
    name='Dam break',
    family='particles',
    group='Water & light',
    aliases=('water column collapse', 'dam burst', 'dam-break simulation'),
    definition='A tall block of water held at one end of a tank is released and slumps into a fast surge '
               'that runs along the floor, crashes up the far wall and sloshes back.',
    phrasings=('let a wall of water go and have it flood across the tank',
               'a fluid sim where the water column collapses and splashes into the other side',
               'lift the gate and let the water rush out'),
    related=('fracture-shatter', 'shatter', 'confetti-burst', 'waterfall-build', 'breaking-news-banner-slam',
             'falling-letter-rain'),
    api=('videobuilder.techniques.particles.dam_break.draw_dam_break',
         'videobuilder.techniques.particles.dam_break.simulate'),
    demo=lambda: demo.film(draw),
)
