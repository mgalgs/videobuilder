"""Thomas attractor: one point follows the three-way symmetric flow
dx/dt = sin(y) - b x (and its two rotations), tracing a looping, knotted
trail that keeps folding back through the centre."""
import functools
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

B = 0.208186   # the classic damping: just below 0.2082, where the motion turns chaotic


def thomas_attractor(steps, start=(0.1, 0.0, 0.0), b=B, dt=0.05, settle=200):
    """`steps` points (x, y, z) of a trajectory through the Thomas flow with
    damping `b`, integrated with fourth-order Runge-Kutta at step `dt` from
    `start`. The first `settle` steps are run and dropped so the trail starts
    on the attractor rather than wandering in from `start`."""
    def f(p):
        x, y, z = p
        return (math.sin(y) - b * x, math.sin(z) - b * y, math.sin(x) - b * z)

    def add(p, k, h):
        return tuple(a + h * c for a, c in zip(p, k))

    p, out = tuple(start), []
    for i in range(settle + steps):
        k1 = f(p)
        k2 = f(add(p, k1, dt / 2))
        k3 = f(add(p, k2, dt / 2))
        k4 = f(add(p, k3, dt))
        p = tuple(a + dt / 6 * (c1 + 2 * c2 + 2 * c3 + c4) for a, c1, c2, c3, c4 in zip(p, k1, k2, k3, k4))
        if i >= settle:
            out.append(p)
    return out


def project(points, cx, cy, scale, spin=0.0, tilt=0.0):
    """Points (x, y, z) to screen (x, y) film px, looking down the attractor's
    symmetry axis (1, 1, 1) so its three lobes show, centred on (cx, cy) and
    `scale` px per unit. `spin` turns it about that axis and `tilt` leans the
    axis back (radians), for a slow 3D turn."""
    s3, s2, s6 = math.sqrt(3), math.sqrt(2), math.sqrt(6)
    ct, st = math.cos(tilt), math.sin(tilt)
    cs, ss = math.cos(spin), math.sin(spin)
    out = []
    for x, y, z in points:
        u, v, w = (x - y) / s2, (x + y - 2 * z) / s6, (x + y + z) / s3   # w along the axis
        u, v = u * cs - v * ss, u * ss + v * cs
        v = v * ct - w * st
        out.append((cx + scale * u, cy - scale * v))
    return out


def draw_attractor(cv, points, color, head=None, width=2, alpha=0.9, fade=8):
    """Draw projected `points` as a trail that brightens toward its newest
    end, in `fade` bands, with a dot on the head in `head` (if given)."""
    if len(points) < 2:
        return
    n = len(points)
    for k in range(fade):
        a, b = k * n // fade, min(n, (k + 1) * n // fade + 1)
        vb.paths.draw(cv, points[a:b], color, width=width, alpha=alpha * (0.25 + 0.75 * (k + 1) / fade))
    if head is not None:
        demo.dot(cv, *points[-1], r=width * 4, color=head)


@functools.lru_cache(maxsize=1)
def _orbit():
    return thomas_attractor(6000, dt=0.06)


def draw(n, cv):
    pts = _orbit()
    p = demo.phase(n, 0.0, 2.8)
    count = max(2, int(len(pts) * (0.06 + 0.94 * p)))
    t = n / demo.FPS
    screen = project(pts[:count], demo.W / 2, demo.H / 2, 70, spin=0.25 * t, tilt=0.18 * math.sin(0.9 * t))
    draw_attractor(cv, screen, '#8f95ff', head=demo.ACCENT, width=1.6)
    cv.mark('attractor', demo.W / 2 - 420, demo.H / 2 - 420, 840, 840)


CAPABILITY = Capability(
    id='thomas-attractor',
    name='Thomas attractor',
    family='particles',
    group='Strange attractors',
    aliases=('cyclically symmetric attractor', "Thomas' cyclically symmetric attractor"),
    definition='A single glowing point traces a never-repeating path through a three-fold symmetric '
               'flow, its trail building into a tangled three-lobed knot that swirls through the centre.',
    phrasings=('a chaotic line that draws itself into a three-petal tangle',
               'a strange attractor trail looping around with triangular symmetry',
               'a point leaving a swirling knotted orbit behind it, like a generative math plot'),
    related=('cyclic-cellular-automaton', 'gravity-well-attraction', 'spinner-ring', 'wander-steering',
             'orbit-loader', 'verlet-rope'),
    api=('videobuilder.capabilities.particles.thomas_attractor.thomas_attractor',
         'videobuilder.capabilities.particles.thomas_attractor.project',
         'videobuilder.capabilities.particles.thomas_attractor.draw_attractor'),
    demo=lambda: demo.film(draw),
)
