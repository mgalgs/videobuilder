"""Particle Trail: a moving emitter sheds a stream of small particles that
drift, shrink and fade behind it, leaving a sparkling wake along its path."""
import math
import random

from ...compendium import kit
from .. import _demo as demo
from ..schema import Capability


def trail_particles(path, t, rate=90, life=0.9, spread=70, drag=0.6, gravity=0.0, seed=0):
    """The live particles of a trail at time `t` (seconds), as `(x, y, age, r)`
    tuples, oldest first: `age` runs 0 (just born) -> 1 (gone), `r` is the
    particle's own seeded random in [0, 1) for size or colour variety.

    `path(s)` is the emitter's (x, y) at time `s`, or None while it is not
    emitting. One particle is born every `1 / rate` seconds at the emitter,
    inheriting `drag` of its backward motion and a random push of up to
    `spread` px/s; `gravity` (px/s^2, positive is down) bends the wake. It is
    stateless: every frame recomputes from `t`, so any frame renders alone."""
    out = []
    dt = 1 / rate
    for k in range(math.floor((t - life) * rate) + 1, math.floor(t * rate) + 1):
        born = k * dt
        age = t - born
        if not 0 <= age < life:
            continue
        here, before = path(born), path(born - dt)
        if here is None:
            continue
        rnd = random.Random(f'{seed}:{k}')
        vx, vy = (0.0, 0.0) if before is None else ((here[0] - before[0]) / dt, (here[1] - before[1]) / dt)
        a, push = rnd.uniform(0, 2 * math.pi), spread * math.sqrt(rnd.random())
        vx, vy = -drag * vx * 0.15 + push * math.cos(a), -drag * vy * 0.15 + push * math.sin(a)
        out.append((here[0] + vx * age, here[1] + vy * age + 0.5 * gravity * age * age, age / life, rnd.random()))
    return out


def draw_particle_trail(cv, path, t, color, size=9, fade_to=None, head=None, **kw):
    """Draw the trail of `path` at time `t`: each particle a dot of up to
    `size` px radius, shrinking and fading as it ages, blending from `color`
    to `fade_to` (default `color`) over its life. `head` draws a dot of that
    radius on the emitter itself. `kw` goes to `trail_particles`. Returns the
    particle list."""
    parts = trail_particles(path, t, **kw)
    for x, y, age, r in parts:
        col = kit.mix(color, fade_to, age) if fade_to else color
        rad = size * (0.55 + 0.45 * r) * (1 - age) ** 0.7
        if rad > 0.3:
            cv.sector(x, y, rad, 0, 2 * math.pi, col, alpha=(1 - age) ** 1.4)
    at = path(t)
    if head and at is not None:
        cv.sector(at[0], at[1], head * 1.9, 0, 2 * math.pi, color, alpha=0.25)
        cv.sector(at[0], at[1], head, 0, 2 * math.pi, '#ffffff')
    return parts


START, END = 0.2, 2.5


def swoop(s):
    """The demo emitter: an S-curve sweep from left to right, live from START to END."""
    if not START <= s <= END:
        return None
    u = (s - START) / (END - START)
    x = demo.W * (0.1 + 0.8 * u)
    y = demo.H / 2 + demo.H * 0.24 * math.sin(u * 2 * math.pi + 0.4)
    return x, y


def draw(n, cv):
    t = n / demo.FPS
    draw_particle_trail(cv, swoop, t, demo.ACCENT, fade_to=demo.TEAL, size=13, head=14,
                        rate=110, life=1.1, spread=70, gravity=40, seed=3)


CAPABILITY = Capability(
    id='particle-trail',
    name='Particle trail',
    family='particles',
    group='Emitters',
    aliases=('particle wake', 'sparkle trail', 'comet trail', 'emitter trail', 'mouse trail', 'sparkle cursor'),
    definition='A moving point leaves a stream of tiny dots behind it that scatter, shrink and fade away, '
               'tracing where it has been.',
    phrasings=('the dot leaves a trail of sparkles as it moves',
               'little particles stream off behind it and fade out',
               'a comet-like tail of glitter following the path'),
    related=('cursor-particle-trail', 'echo-trail-type', 'particle-morph', 'orbit-loader',
             'player-movement-trail', 'lightning-bolt'),
    api=('videobuilder.capabilities.particles.particle_trail.draw_particle_trail',
         'videobuilder.capabilities.particles.particle_trail.trail_particles'),
    demo=lambda: demo.film(draw),
)
