"""Path emitter: particles are born on a path rather than at one point --
either all along it, or at a head that runs along it -- and drift off,
shrinking and fading, so the path is traced in sparks."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def point_on_path(points, f, closed=False):
    """The point at fraction `f` (0 -> 1) of `points` by arc length, and the
    unit tangent there, as `((x, y), (tx, ty))`."""
    pts = vb.paths.reveal(points, max(f, 1e-6), closed=closed)
    if len(pts) < 2:
        pts = list(points[:2])
    (x0, y0), (x1, y1) = pts[-2], pts[-1]
    d = math.hypot(x1 - x0, y1 - y0) or 1.0
    return pts[-1], ((x1 - x0) / d, (y1 - y0) / d)


def path_particles(points, t, rate=60, life=1.2, sweep=(0.0, 2.0), speed=120, spread=0.6,
                   gravity=(0, 60), size=8, seed=0, closed=False):
    """Every particle alive at time `t` (seconds) emitted from the path
    `points`, as `(x, y, radius, alpha)` tuples, oldest first.

    With `sweep` a `(start, end)` pair in seconds, a head runs the path from
    end to end across that window and `rate` particles a second are born
    where the head is. With `sweep=None`, births start at 0 s and go on
    forever, each at a random place along the whole path. A particle
    leaves along the path's normal (either side), `spread` radians of random
    fan, at about `speed` px/s, falls with `gravity` px/s^2, and over `life`
    seconds shrinks from `size` and fades out. Stateless and seeded: the same
    arguments give the same particles on every frame."""
    start, end = sweep if sweep else (0.0, math.inf)
    first = max(0, math.floor((t - life - start) * rate))
    last = math.floor((min(t, end) - start) * rate)
    gx, gy = gravity
    out = []
    for i in range(first, last + 1):
        born = start + i / rate
        age = t - born
        if age < 0 or age >= life:
            continue
        rnd = random.Random(f'{seed}:{i}')
        f = (born - start) / (end - start) if sweep else rnd.random()
        (x, y), (tx, ty) = point_on_path(points, f, closed)
        side = 1 if rnd.random() < 0.5 else -1
        a = math.atan2(tx * side, -ty * side) + rnd.uniform(-spread, spread)  # around the normal
        v = speed * rnd.uniform(0.4, 1.0)
        k = age / life
        out.append((x + math.sin(a) * v * age + 0.5 * gx * age * age,
                    y - math.cos(a) * v * age + 0.5 * gy * age * age,
                    size * rnd.uniform(0.5, 1.0) * (1 - k * 0.7),
                    (1 - k) ** 1.5))
    return out


def draw_path_emitter(cv, points, t, color, **kw):
    """Draw the particles `path_particles(points, t, **kw)` gives as dots of
    `color`. Returns the particle list."""
    parts = path_particles(points, t, **kw)
    for x, y, r, alpha in parts:
        cv.sector(x, y, r, 0, 2 * math.pi, color, alpha=alpha)
    return parts


# The demo: an S-curve across the frame, a head running it, sparks thrown off.
PATH = [(demo.W * (0.1 + 0.8 * s / 80),
         demo.H * (0.5 - 0.22 * math.sin(s / 80 * 2 * math.pi))) for s in range(81)]
SWEEP = (0.2, 2.1)


def draw(n, cv):
    t = n / demo.FPS
    p = demo.phase(n, *SWEEP)
    vb.paths.draw(cv, PATH, demo.LINE, width=3, alpha=0.6)
    vb.paths.draw(cv, vb.paths.reveal(PATH, p), demo.MUTED, width=3)
    draw_path_emitter(cv, PATH, t, demo.TEAL, rate=80, life=1.2, sweep=SWEEP, speed=220, size=9, seed=3)
    draw_path_emitter(cv, PATH, t, demo.ACCENT, rate=50, life=0.9, sweep=SWEEP, speed=140, size=7, seed=4)
    if 0 < p < 1:
        (x, y), _ = point_on_path(PATH, p)
        demo.dot(cv, x, y, r=14, color=demo.INK)


TECHNIQUE = Technique(
    id='path-emitter',
    name='Path emitter',
    family='particles',
    group='Emitters',
    aliases=('emit along path', 'path particles', 'spline emitter', 'line emitter'),
    definition='Particles spawn along a line or curve, often from a head that travels it, '
               'then drift away and fade so the shape is traced in sparks.',
    phrasings=('sparks fly off the line as it draws across the screen',
               'particles pour out all along the curve',
               'a glowing point runs along the path shedding particles behind it'),
    related=('path-follow-motion', 'player-movement-trail', 'cursor-particle-trail', 'wiggle-path',
             'text-on-a-path', 'map-route-draw'),
    api=('videobuilder.techniques.particles.path_emitter.draw_path_emitter',
         'videobuilder.techniques.particles.path_emitter.path_particles',
         'videobuilder.techniques.particles.path_emitter.point_on_path'),
    demo=lambda: demo.film(draw),
)
