"""SPH Fluid: a liquid made of many small particles, each pushed by how crowded
its neighbours are, so the crowd pours, splashes and settles like water.

The solver is the particle-based scheme of double density relaxation: every
step each particle measures its density from neighbours within `h`, and
pressure pushes pairs apart (or pulls them together a little, which gives
surface tension). It works in film px, so a film can drop the result
straight onto a canvas. Pure Python with a grid for neighbour search: a few
hundred particles over a few seconds simulate in a couple of seconds.
"""
import math
from functools import lru_cache

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


class SPHFluid:
    """A 2D particle fluid inside the box (`left`, `top`, `right`, `bottom`).

    `points`: starting (x, y) of each particle, in px. `h`: interaction
    radius, about twice the starting spacing. `gravity`: px per step squared.
    `density`: the rest density (a particle's neighbour count, weighted);
    `stiffness` and `near`: how hard crowding pushes back; `viscosity`:
    how much neighbours drag each other's velocity together. `walls` is a
    list of extra vertical barriers as `[x, top, bottom]`, which may be
    edited between steps (a gate that lifts). Call `step()` to advance;
    read `x`, `y`, `vx`, `vy`."""

    def __init__(self, points, box, h=24.0, gravity=0.15, density=2.0, stiffness=1.0, near=1.0,
                 viscosity=0.08, walls=()):
        self.x = [float(p[0]) for p in points]
        self.y = [float(p[1]) for p in points]
        self.vx = [0.0] * len(self.x)
        self.vy = [0.0] * len(self.x)
        self.box = box
        self.h, self.gravity, self.density = h, gravity, density
        self.stiffness, self.near, self.viscosity = stiffness, near, viscosity
        self.walls = [list(w) for w in walls]

    def _pairs(self):
        """Every pair (i, j, q, ux, uy) closer than `h`: q = distance / h,
        (ux, uy) the unit vector from i to j."""
        h = self.h
        grid = {}
        xs, ys = self.x, self.y
        for i in range(len(xs)):
            grid.setdefault((int(xs[i] // h), int(ys[i] // h)), []).append(i)
        out = []
        for (cx, cy), cell in grid.items():
            for ox, oy in ((0, 0), (1, 0), (-1, 1), (0, 1), (1, 1)):
                other = grid.get((cx + ox, cy + oy))
                if other is None:
                    continue
                same = ox == 0 and oy == 0
                for a, i in enumerate(cell):
                    xi, yi = xs[i], ys[i]
                    for j in (cell[a + 1:] if same else other):
                        dx, dy = xs[j] - xi, ys[j] - yi
                        d2 = dx * dx + dy * dy
                        if d2 < h * h and d2 > 1e-9:
                            d = math.sqrt(d2)
                            out.append((i, j, d / h, dx / d, dy / d))
        return out

    def step(self):
        """Advance one step: gravity, viscosity, move, relax density, collide."""
        x, y, vx, vy = self.x, self.y, self.vx, self.vy
        n = len(x)
        for i in range(n):
            vy[i] += self.gravity
        pairs = self._pairs()
        if self.viscosity:
            for i, j, q, ux, uy in pairs:
                u = (vx[i] - vx[j]) * ux + (vy[i] - vy[j]) * uy
                if u > 0:
                    imp = 0.5 * (1 - q) * self.viscosity * u
                    vx[i] -= imp * ux
                    vy[i] -= imp * uy
                    vx[j] += imp * ux
                    vy[j] += imp * uy
        px, py = x[:], y[:]
        for i in range(n):
            x[i] += vx[i]
            y[i] += vy[i]
        self._relax()
        self._collide(px)
        for i in range(n):
            vx[i] = x[i] - px[i]
            vy[i] = y[i] - py[i]

    def _relax(self):
        """Double density relaxation, particle by particle, each seeing the
        moves already made (which keeps it stable at large steps)."""
        x, y, h = self.x, self.y, self.h
        near = [[] for _ in x]
        for i, j, _, _, _ in self._pairs():
            near[i].append(j)
            near[j].append(i)
        h2 = h * h
        for i, others in enumerate(near):
            xi, yi = x[i], y[i]
            found = []
            rho = rho_near = 0.0
            for j in others:
                dx, dy = x[j] - xi, y[j] - yi
                d2 = dx * dx + dy * dy
                if 1e-9 < d2 < h2:
                    d = math.sqrt(d2)
                    a = 1 - d / h
                    rho += a * a
                    rho_near += a * a * a
                    found.append((j, a, dx / d, dy / d))
            press = self.stiffness * (rho - self.density)
            press_near = self.near * rho_near
            mx = my = 0.0
            for j, a, ux, uy in found:
                d = 0.5 * (press * a + press_near * a * a)
                x[j] += d * ux
                y[j] += d * uy
                mx -= d * ux
                my -= d * uy
            x[i] += mx
            y[i] += my

    def _collide(self, px):
        left, top, right, bottom = self.box
        x, y = self.x, self.y
        for i in range(len(x)):
            if x[i] < left:
                x[i] = left
            elif x[i] > right:
                x[i] = right
            if y[i] > bottom:
                y[i] = bottom
            elif y[i] < top:
                y[i] = top
            for wx, wtop, wbottom in self.walls:
                if wtop <= y[i] <= wbottom and (px[i] - wx) * (x[i] - wx) <= 0:
                    x[i] = wx - 0.5 if px[i] < wx else wx + 0.5


def simulate(fluid, frames, substeps=2, before=None):
    """Run `fluid` for `frames` frames of `substeps` steps each and return one
    snapshot per frame: a list of `(x, y, speed)` per particle, speed in px
    per step. `before(fluid, frame)` runs before each frame's steps, to move
    walls or push particles. Frame 0 is the starting state."""
    out = []
    for f in range(frames):
        if f:
            if before:
                before(fluid, f)
            for _ in range(substeps):
                fluid.step()
        out.append([(fluid.x[i], fluid.y[i], math.hypot(fluid.vx[i], fluid.vy[i]))
                    for i in range(len(fluid.x))])
    return out


def draw_fluid(cv, snapshot, radius=8.0, color=demo.TEAL, foam=demo.INK, fast=6.0):
    """Draw one `simulate` snapshot as liquid: a soft wide pass that merges
    neighbouring particles into one body, then each particle as a dot tinted
    from `color` towards `foam` as its speed nears `fast`."""
    with cv.layer(opacity=0.35):
        for x, y, _ in snapshot:
            demo.dot(cv, x, y, radius * 1.9, color=color)
    base, top = vb.rgba(color), vb.rgba(foam)
    for x, y, s in snapshot:
        t = vb.clamp01(s / fast) ** 1.5
        demo.dot(cv, x, y, radius, color=tuple(255 * (b + (c - b) * t) for b, c in zip(base[:3], top[:3])))


# The demo: a dam break. A column of water held by a gate on the left of a
# tank; the gate lifts, the column collapses, runs across the floor, slaps
# the far wall and sloshes back.
LEFT, RIGHT, TOP, FLOOR = 220, 740, 110, 470
GATE_X, GATE_LIFT = 400, 0.35
SPACING = 11


def _gate(fluid, f):
    if f / demo.FPS >= GATE_LIFT:
        fluid.walls = []


@lru_cache(maxsize=1)
def _run():
    pts = [(LEFT + 6 + c * SPACING + (r % 2) * SPACING / 2, FLOOR - 6 - r * SPACING)
           for r in range(24) for c in range(int((GATE_X - LEFT - 12) / SPACING))]
    fluid = SPHFluid(pts, (LEFT, TOP - 400, RIGHT, FLOOR), h=SPACING * 2.2,
                     walls=[(GATE_X, TOP - 400, FLOOR)])
    for _ in range(200):  # settle the column behind the gate, damped, so frame 0 is still
        fluid.step()
        fluid.vx = [v * 0.7 for v in fluid.vx]
        fluid.vy = [v * 0.7 for v in fluid.vy]
    return simulate(fluid, round(demo.SECONDS * demo.FPS), before=_gate)


def draw(n, cv):
    snap = _run()[n]
    t = n / demo.FPS
    gate_up = vb.clamp01((t - GATE_LIFT) / 0.25) * 420
    cv.line(LEFT - 4, TOP, LEFT - 4, FLOOR + 4, demo.MUTED, width=6)
    cv.line(RIGHT + 4, TOP, RIGHT + 4, FLOOR + 4, demo.MUTED, width=6)
    cv.line(LEFT - 7, FLOOR + 4, RIGHT + 7, FLOOR + 4, demo.MUTED, width=6)
    draw_fluid(cv, snap, radius=SPACING * 0.62)
    if gate_up < 420:
        cv.rect(GATE_X - 4, TOP - 30 - gate_up, 8, FLOOR - TOP + 30, demo.ACCENT)
    xs = [p[0] for p in snap]
    ys = [p[1] for p in snap]
    cv.mark('fluid', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


CAPABILITY = Capability(
    id='sph-fluid',
    name='SPH fluid',
    family='particles',
    group='Fluids',
    aliases=('smoothed particle hydrodynamics', 'particle fluid', 'particle liquid', 'dam break'),
    definition='A body of liquid built from many small particles that push away from crowded neighbours, '
               'so it pours, splashes off walls and sloshes to rest like real water.',
    phrasings=('simulated water made of particles that splashes around a tank',
               'release a column of liquid and let it collapse and slosh realistically',
               'a physics-driven fluid that pours and settles'),
    related=('animated-sprite-particles', 'glitter-pour', 'liquid-fill-level', 'curl-noise-flow',
             'smoke-puffs', 'liquid-morph'),
    api=('videobuilder.capabilities.particles.sph_fluid.SPHFluid',
         'videobuilder.capabilities.particles.sph_fluid.simulate',
         'videobuilder.capabilities.particles.sph_fluid.draw_fluid'),
    demo=lambda: demo.film(draw),
)
