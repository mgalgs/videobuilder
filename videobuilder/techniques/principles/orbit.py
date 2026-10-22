"""Orbit: a body circles a centre on a steady loop, the ring tipped toward the
viewer so it swings in front of the centre and passes behind it."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def orbit(cx, cy, radius, t, period=1.0, phase=0.0, tilt=0.35, spin=1):
    """Where an orbiting body is at time `t`: `(x, y, depth)`. The ring is a
    circle of `radius` about (cx, cy), seen from above at `tilt` (1 = face on,
    0 = edge on), so it reads as an ellipse `radius` wide and `radius * tilt`
    tall. One turn takes `period` (in `t`'s units); `phase` is the starting
    angle in turns; `spin` is 1 or -1 for the direction. `depth` runs -1
    (farthest, behind the centre) to 1 (nearest, in front): draw a body
    before the centre while `depth < 0`, and scale or fade it by depth."""
    a = 2 * math.pi * (spin * t / period + phase)
    return cx + radius * math.cos(a), cy + radius * tilt * math.sin(a), math.sin(a)


def ring(cx, cy, radius, tilt=0.35, n=96):
    """The orbit's path as points, for `vb.paths.draw(..., closed=True)`."""
    return [orbit(cx, cy, radius, i / n, tilt=tilt)[:2] for i in range(n)]


def draw(n, cv):
    cx, cy, r, tilt = demo.W / 2, demo.H / 2, 440, 0.2
    t = n / demo.FPS
    path = ring(cx, cy, r, tilt)
    vb.paths.draw(cv, path, demo.MUTED, width=3, closed=True, alpha=0.45)
    x, y, depth = orbit(cx, cy, r, t, period=demo.SECONDS, phase=0.25, tilt=tilt)
    size = 34 * (1 + 0.3 * depth)  # nearer is bigger
    trail = [orbit(cx, cy, r, t - k * 0.03, period=demo.SECONDS, phase=0.25, tilt=tilt) for k in range(1, 9)]

    def body():
        for k, (tx, ty, td) in enumerate(trail):
            demo.dot(cv, tx, ty, 34 * (1 + 0.3 * td) * (1 - k / 10), alpha=0.25 * (1 - k / 9))
        demo.dot(cv, x, y, size)
        cv.mark('satellite', x - size, y - size, 2 * size, 2 * size)

    if depth < 0:
        body()
    demo.dot(cv, cx, cy, 90, color=demo.TEAL)
    cv.mark('centre', cx - 90, cy - 90, 180, 180)
    vb.paths.draw(cv, path[:len(path) // 2 + 1], demo.MUTED, width=3, alpha=0.45)  # the near half crosses the centre
    if depth >= 0:
        body()


TECHNIQUE = Technique(
    id='orbit',
    name='Orbit',
    family='principles',
    group='Physics',
    aliases=('orbital motion', 'circular orbit', 'revolve'),
    definition='An object travels round and round a central point on a fixed loop, '
               'passing in front of the centre and then behind it.',
    phrasings=('a small dot circling around a big one like a moon',
               'make it revolve around the logo',
               'something going round the centre like a planet'),
    related=('two-body-orbit', 'orbiting-characters', 'orbital-pulse', 'orbit-loader', 'spiral-galaxy',
             'orbit-shot'),
    api=('videobuilder.techniques.principles.orbit.orbit',
         'videobuilder.techniques.principles.orbit.ring'),
    demo=lambda: demo.film(draw),
)
