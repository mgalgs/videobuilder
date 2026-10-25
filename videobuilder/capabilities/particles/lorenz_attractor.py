"""Lorenz attractor: a single point follows the Lorenz equations and its
path, drawn as a glowing line, loops round one wing then the other without
ever retracing itself, sketching the two-lobed butterfly."""
import math
from functools import lru_cache

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def lorenz_trajectory(steps, dt=0.01, start=(0.1, 0.0, 0.0), sigma=10.0, rho=28.0, beta=8 / 3, settle=0):
    """`steps` (x, y, z) states of the Lorenz system from `start`, `dt` apart
    (fourth-order Runge-Kutta). `settle` steps are integrated first and
    dropped, so the path starts already on the attractor."""
    def f(x, y, z):
        return sigma * (y - x), x * (rho - z) - y, x * y - beta * z

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


def project_attractor(states, cx, cy, size, yaw=0.0, tilt=0.0, rho=28.0):
    """Lorenz `states` -> (x, y) film px: the attractor (about 50 units wide,
    centred near z = `rho` - 1) turned `yaw` radians about its vertical z axis,
    tipped `tilt` radians towards the viewer, scaled so its width is about
    `size` px and centred on (cx, cy), wings left and right, z up."""
    k = size / 50
    cyaw, syaw = math.cos(yaw), math.sin(yaw)
    ct, st = math.cos(tilt), math.sin(tilt)
    out = []
    for x, y, z in states:
        u = x * cyaw - y * syaw
        depth = x * syaw + y * cyaw
        v = (z - (rho - 1)) * ct - depth * st
        out.append((cx + u * k, cy - v * k))
    return out


def draw_trace(cv, points, color, head_color=None, width=2.0, tail=160, alpha=1.0):
    """Stroke a projected trajectory as a glowing line: the whole path faint,
    its last `tail` points brightening towards a lit head dot."""
    if len(points) < 2:
        return
    vb.paths.draw(cv, points, color, width=width * 0.6, alpha=0.32 * alpha)
    recent = points[-tail:]
    seg = 12
    for i in range(0, len(recent) - 1, seg):
        a = (i + seg) / len(recent)
        chunk = recent[i:i + seg + 1]
        vb.paths.draw(cv, chunk, color, width=width * 3.2, alpha=0.10 * a * alpha)
        vb.paths.draw(cv, chunk, head_color or color, width=width, alpha=(0.35 + 0.65 * a) * alpha)
    hx, hy = points[-1]
    demo.dot(cv, hx, hy, width * 5, head_color or color, alpha=0.25 * alpha)
    demo.dot(cv, hx, hy, width * 1.8, demo.INK, alpha=alpha)
    cv.mark('head', hx - 6, hy - 6, 12, 12)


@lru_cache(maxsize=None)
def _path():
    return lorenz_trajectory(2400, dt=0.008, start=(1.0, 1.0, 1.0), settle=2000)


def draw(n, cv):
    p = n / (demo.FPS * demo.SECONDS)
    shown = 900 + round(1500 * p)   # opens with both wings sketched, then keeps tracing
    pts = project_attractor(_path()[:shown], demo.W / 2, demo.H / 2, 500, yaw=-0.05 - 0.35 * p, tilt=0.1)
    draw_trace(cv, pts, '#7f8cff', head_color='#f2c84b', width=2.0)


CAPABILITY = Capability(
    id='lorenz-attractor',
    name='Lorenz attractor',
    family='particles',
    group='Strange attractors',
    aliases=('butterfly attractor', 'Lorenz system', 'chaotic attractor'),
    definition='A single glowing line traces a never-repeating path that loops around one wing and then the '
               'other, gradually drawing a butterfly-shaped figure eight in 3D.',
    phrasings=('a chaotic line that keeps looping into a butterfly shape',
               'draw the classic chaos-theory butterfly swirl',
               'a glowing trail orbiting two lobes and never quite repeating'),
    related=('gravity-well-attraction', 'swirl', 'fireflies', 'kuramoto-synchronization',
             'turbulence-displacement', 'spiral-galaxy'),
    api=('videobuilder.capabilities.particles.lorenz_attractor.lorenz_trajectory',
         'videobuilder.capabilities.particles.lorenz_attractor.project_attractor',
         'videobuilder.capabilities.particles.lorenz_attractor.draw_trace'),
    demo=lambda: demo.film(draw),
)
