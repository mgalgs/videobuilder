"""Fountain: a steady jet of particles leaves one point going up, each one
curving over under gravity and dropping back down to the ground."""
import math
import random

from .. import _demo as demo
from ..schema import Capability


def fountain(t, x, y, rate=120, speed=720, spread=0.22, jitter=0.15, gravity=900, floor=None,
             start=0.0, stop=None, seed=0):
    """The particles of a fountain at `t` seconds, as `(px, py, vx, vy, age)`
    tuples. They leave (x, y) at `rate` per second from `start` (until `stop`,
    if given), heading up at about `speed` px/s, tilted off vertical by up to
    `spread` radians and with `jitter` (a fraction) of random speed, then fall
    at `gravity` px/s^2. A particle is gone once it drops below `floor`
    (default: the source's own height). Stateless: any `t` can be asked for in
    any order, and the same `seed` gives the same spray."""
    floor = y if floor is None else floor
    end = t if stop is None else min(t, stop)
    out = []
    i = 0
    while True:
        born = start + i / rate
        if born > end:
            break
        r = random.Random(f'{seed}:{i}')
        i += 1
        angle = r.uniform(-spread, spread)
        v = speed * (1 + r.uniform(-jitter, jitter))
        vx, vy = v * math.sin(angle), -v * math.cos(angle)
        age = t - born
        py = y + vy * age + 0.5 * gravity * age * age
        if py > floor and age > 0:
            continue
        out.append((x + vx * age, py, vx, vy + gravity * age, age))
    return out


def draw_fountain(cv, particles, color=demo.INK, r=3.0, trail=0.03, alpha=1.0):
    """Draw `fountain` particles as small dots, each with a faint streak
    `trail` seconds long behind it along its motion."""
    for px, py, vx, vy, age in particles:
        if trail:
            cv.line(px - vx * trail, py - vy * trail, px, py, color, width=r, alpha=0.35 * alpha)
        demo.dot(cv, px, py, r=r, color=color, alpha=alpha)


def draw(n, cv):
    x, ground = demo.W / 2, demo.H - 70
    demo.floor(cv, ground, color=demo.LINE)
    cv.rect(x - 22, ground - 12, 44, 12, demo.TEAL, radius=4)   # the nozzle
    t = n / demo.FPS
    draw_fountain(cv, fountain(t, x, ground - 12, floor=ground, start=0.1, seed=3), color=demo.INK)
    cv.mark('fountain', x - 260, 60, 520, ground - 60)


CAPABILITY = Capability(
    id='fountain',
    name='Fountain',
    family='particles',
    group='Emitters',
    aliases=('jet emitter', 'upward spray'),
    definition='A stream of particles leaves one point heading upward, bends over under gravity '
               'and rains back down around its source.',
    phrasings=('particles spraying up and falling back like a water fountain',
               'a jet of sparks that shoots up and arcs down to the ground',
               'make the dots gush upward from one spot and drop back down'),
    related=('particle-morph', 'curl-noise-flow', 'flow-field', 'confetti-burst', 'ripple',
             'k-rm-n-vortex-street'),
    api=('videobuilder.capabilities.particles.fountain.fountain',
         'videobuilder.capabilities.particles.fountain.draw_fountain'),
    demo=lambda: demo.film(draw),
)
