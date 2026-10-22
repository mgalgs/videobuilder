"""Animated sprite particles: an emitter whose particles are not still dots
but little flipbooks, each stepping through its own frames (a sparkle that
pops, a coin that spins) as it drifts along its path."""
import math
import random

from .. import _demo as demo
from ..schema import Capability


def particles(t, rate=12.0, life=1.6, seed=0, box=(0, 0, 1920, 1080), speed=(40, 120), angle=-math.pi / 2,
              spread=math.pi / 3, gravity=0.0):
    """The particles alive at time `t` seconds, as dicts with `x`, `y`,
    `age` (0 -> 1 across the particle's `life`), `seconds` (its age in
    seconds) and `i` (its index, for per-particle choices). One is born every
    1/`rate` s at a random point in `box` (x, y, w, h) and flies at `speed`
    (min, max px/s) along `angle` +/- `spread`/2 (radians, canvas y down), with
    `gravity` px/s^2 pulling down. The emitter is pre-warmed, so the frame is
    already full at t = 0, and the same `seed` gives the same particles."""
    bx, by, bw, bh = box
    out = []
    first, last = math.floor((t - life) * rate) + 1, math.floor(t * rate)
    for i in range(first, last + 1):
        born = i / rate
        age = t - born
        if not 0 <= age < life:
            continue
        r = random.Random(f'{seed}:{i}')
        x0, y0 = bx + r.random() * bw, by + r.random() * bh
        a = angle + (r.random() - 0.5) * spread
        v = speed[0] + r.random() * (speed[1] - speed[0])
        out.append({'x': x0 + math.cos(a) * v * age, 'y': y0 + math.sin(a) * v * age + 0.5 * gravity * age * age,
                    'age': age / life, 'seconds': age, 'i': i})
    return out


def sprite_frame(particle, frames, fps=None, loop=False):
    """Which of `frames` sprite frames `particle` shows. By default the
    flipbook plays once across the particle's life; with `fps` it steps at
    that rate instead, holding its last frame (or wrapping, with `loop`).
    Each particle starts at its own age, so neighbours are never in step."""
    if fps is None:
        k = int(particle['age'] * frames)
    else:
        k = int(particle['seconds'] * fps)
        if loop:
            return k % frames
    return min(k, frames - 1)


def draw_sprite_particles(cv, t, sprite, frames, fps=None, loop=False, size=40, colors=(demo.INK,), **kw):
    """Draw the emitter at time `t`: every particle from `particles(t, **kw)`
    drawn as `sprite(cv, frame, x, y, size, color)` at its own flipbook
    frame (see `sprite_frame`), its colour picked from `colors` per particle.
    Returns the particles drawn."""
    ps = particles(t, **kw)
    for p in ps:
        color = colors[random.Random(f'c:{p["i"]}').randrange(len(colors))]
        sprite(cv, sprite_frame(p, frames, fps, loop), p['x'], p['y'], size, color)
    return ps


SPARKLE_FRAMES = 8


def sparkle(cv, frame, x, y, size, color):
    """A ready-made eight-frame sprite, a sparkle popping: a dot swells
    (0-1), flashes into an eight-ray star that grows (2-4), then breaks into
    a ring of dots that widens and fades (5-7). Drawn in discrete steps, not
    tweened, so it reads as a flipbook. Fits `draw_sprite_particles`."""
    s = size / 40
    if frame <= 1:
        demo.dot(cv, x, y, (3 + 3 * frame) * s, color)
    elif frame <= 4:
        reach = (10 + 7 * (frame - 2)) * s
        for k in range(8):
            a = k * math.pi / 4
            ln = reach if k % 2 == 0 else reach * 0.6
            cv.line(x, y, x + math.cos(a) * ln, y + math.sin(a) * ln, color, width=3 * s)
        demo.dot(cv, x, y, 4 * s, color)
    else:
        ring = (22 + 8 * (frame - 5)) * s
        for k in range(10):
            a = k * math.pi / 5
            demo.dot(cv, x + math.cos(a) * ring, y + math.sin(a) * ring, 2.6 * s, color,
                     alpha=1 - 0.3 * (frame - 5))


def draw(n, cv):
    t = n / demo.FPS
    # The sprite sheet itself, faint along the bottom, so the frames each particle plays are visible.
    step, cell = 60, 48
    x0, y = demo.W / 2 - (SPARKLE_FRAMES - 1) * step / 2, demo.H - 44
    for k in range(SPARKLE_FRAMES):
        cv.outline(x0 + k * step - cell / 2, y - cell / 2, cell, cell, demo.LINE, width=1.5, radius=6)
        sparkle(cv, k, x0 + k * step, y, 16, demo.MUTED)
    cv.mark('sheet', x0 - cell / 2, y - cell / 2, (SPARKLE_FRAMES - 1) * step + cell, cell)
    draw_sprite_particles(cv, t, sparkle, SPARKLE_FRAMES, fps=9, size=26, colors=(demo.ACCENT, '#f2c14e', demo.INK),
                          rate=14, life=SPARKLE_FRAMES / 9, seed=3, box=(100, 60, demo.W - 200, demo.H - 170),
                          speed=(15, 45), spread=math.pi * 0.8)


CAPABILITY = Capability(
    id='animated-sprite-particles',
    name='Animated sprite particles',
    family='particles',
    group='Emitters',
    aliases=('sprite sheet particles', 'frame-based particles', 'flipbook particles'),
    definition='An emitter whose particles each play their own little frame-by-frame animation, '
               'out of step with one another, while they drift across the screen.',
    phrasings=('particles that are tiny animations, like sparkles that pop as they float',
               'use a sprite sheet for each particle so they animate while moving',
               'a swarm of little twinkling stars, each one cycling through its frames'),
    related=('flipbook-sprite-animation', 'particle-morph', 'sph-fluid', 'image-to-particles',
             'particle-swarm-assemble', 'audio-reactive-particles'),
    api=('videobuilder.capabilities.particles.animated_sprite_particles.draw_sprite_particles',
         'videobuilder.capabilities.particles.animated_sprite_particles.particles',
         'videobuilder.capabilities.particles.animated_sprite_particles.sprite_frame',
         'videobuilder.capabilities.particles.animated_sprite_particles.sparkle'),
    demo=lambda: demo.film(draw),
)
