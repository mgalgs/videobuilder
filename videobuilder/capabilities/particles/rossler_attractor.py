"""Rossler attractor: a point following the Rossler equations circles
outward in a flat spiral, is flung up into a fold, and drops back near the
centre, so its trail builds a twisted band that never quite repeats.

`rossler` integrates the path in 3-D; `project` turns it into screen
points for a given view; `draw_rossler` draws the trail traced so far.
"""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def rossler(steps, dt=0.02, a=0.2, b=0.2, c=5.7, start=(1.0, 1.0, 0.0), settle=2000):
    """`steps` points (x, y, z) along the Rossler flow
    dx = -y - z, dy = x + a y, dz = b + z (x - c), one every `dt` time units
    (Runge-Kutta 4). The first `settle` steps are run and dropped so the
    path starts on the attractor rather than drifting onto it. The classic
    a = b = 0.2, c = 5.7 gives the single-fold band; raise `c` for more
    chaos, lower it (around 2.5-4) for a plain or doubled loop."""
    def f(x, y, z):
        return -y - z, x + a * y, b + z * (x - c)

    x, y, z = start
    out = []
    for i in range(settle + steps):
        k1 = f(x, y, z)
        k2 = f(x + dt / 2 * k1[0], y + dt / 2 * k1[1], z + dt / 2 * k1[2])
        k3 = f(x + dt / 2 * k2[0], y + dt / 2 * k2[1], z + dt / 2 * k2[2])
        k4 = f(x + dt * k3[0], y + dt * k3[1], z + dt * k3[2])
        x += dt / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        y += dt / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        z += dt / 6 * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2])
        if i >= settle:
            out.append((x, y, z))
    return out


def project(points, cx, cy, scale, yaw=0.0, tilt=0.35, center=(0.0, 0.0, 6.0)):
    """3-D `points` as screen (x, y): turned `yaw` radians about the
    vertical (z) axis, then viewed from `tilt` radians above the x-y plane
    (0 = edge on, pi/2 = straight down), with `center` placed at (cx, cy)
    and `scale` px per unit. z points up the screen."""
    cy_, sy_ = math.cos(yaw), math.sin(yaw)
    ct, st = math.cos(tilt), math.sin(tilt)
    ox, oy, oz = center
    out = []
    for x, y, z in points:
        x, y, z = x - ox, y - oy, z - oz
        rx, ry = x * cy_ - y * sy_, x * sy_ + y * cy_
        out.append((cx + scale * rx, cy - scale * (z * ct + ry * st)))
    return out


def draw_rossler(cv, points, p, cx, cy, scale, yaw=0.0, tilt=0.35, trail=demo.MUTED, head=demo.ACCENT,
                 tail=160, chunk=120, width=1.6, trail_alpha=0.28):
    """Draw the 3-D path `points` (from `rossler`) traced up to progress
    `p` (0 -> 1), seen through `project`. The whole trail so far is drawn
    faintly in short strokes, so loops that pass over each other thicken
    into the band; the latest `tail` points are drawn bright with a dot at
    the tip. Returns the tip's screen (x, y)."""
    count = max(2, round(len(points) * vb.clamp01(p)))
    pts = project(points[:count], cx, cy, scale, yaw, tilt)
    for i in range(0, count - 1, chunk):
        vb.paths.draw(cv, pts[i:i + chunk + 1], trail, width=width, alpha=trail_alpha)
    recent = pts[-tail:]
    vb.paths.draw(cv, recent[: len(recent) // 2 + 1], head, width=width + 0.6, alpha=0.5)
    vb.paths.draw(cv, recent[len(recent) // 2:], head, width=width + 1.2)
    tx, ty = pts[-1]
    demo.dot(cv, tx, ty, r=11, color=head, alpha=0.3)
    demo.dot(cv, tx, ty, r=5, color=head)
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    cv.mark('attractor', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
    return tx, ty


_PATH = []


def draw(n, cv):
    if not _PATH:
        _PATH.extend(rossler(6000, dt=0.025))
    t = n / demo.FPS
    p = 0.04 + 0.96 * demo.phase(n, 0.0, 2.8) ** 1.4
    draw_rossler(cv, _PATH, p, demo.W / 2 - 10, demo.H / 2 + 50, 17, yaw=-0.5 + 0.25 * t, tilt=0.38)


CAPABILITY = Capability(
    id='rossler-attractor',
    name='Rossler attractor',
    family='particles',
    group='Strange attractors',
    aliases=('Rössler attractor', 'Rossler system', 'Rossler band', 'chaotic spiral attractor'),
    definition='A glowing point spirals outward on a flat disc, gets thrown up into a looping fold and drops '
               'back to the middle, its trail weaving a twisted band that never exactly repeats.',
    phrasings=('trace a chaotic spiral that loops up and folds back over itself',
               'draw one of those strange attractor trails, the spiral-with-a-hump one',
               'a point swirling round a disc and flicking up into an arch, leaving a band of lines'),
    related=('gravity-well-attraction', 'spinner-ring', 'wander-steering', 'wiggle-path', 'spiral-galaxy',
             'radial-repeater'),
    api=('videobuilder.capabilities.particles.rossler_attractor.draw_rossler',
         'videobuilder.capabilities.particles.rossler_attractor.rossler',
         'videobuilder.capabilities.particles.rossler_attractor.project'),
    demo=lambda: demo.film(draw),
)
