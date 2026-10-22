"""Particle Life: dots of a few colours, each colour pulled toward or pushed
from every other colour by its own rule, so a uniform scatter organises itself
into clumps, chasing pairs, chains and rings."""
import functools
import math
import random

from .. import _demo as demo
from ..schema import Capability


def life_force(d, pull, core=0.3):
    """The force between two particles `d` apart, `d` in units of the
    interaction radius: a short push-apart inside `core` whatever the rule (so
    clumps don't collapse to a point), then a tent of strength `pull` (+ draws
    in, - drives off) that peaks halfway out and is 0 at the radius."""
    if d < core:
        return d / core - 1
    if d < 1:
        return pull * (1 - abs(2 * d - 1 - core) / (1 - core))
    return 0.0


def random_rules(species, seed=0, lo=-1.0, hi=1.0):
    """A seeded `species` x `species` rule table: `rules[a][b]` is how much
    colour `a` is drawn to (+) or pushed from (-) colour `b`."""
    rnd = random.Random(f'rules:{seed}')
    return tuple(tuple(rnd.uniform(lo, hi) for _ in range(species)) for _ in range(species))


@functools.lru_cache(maxsize=8)
def particle_life(rules, count, size, steps, seed=0, radius=110.0, strength=1.5, friction=0.86,
                  wrap=True):
    """Run a particle-life world and return its frames: `steps + 1` tuples of
    `(x, y, species)` triples, frame 0 being the seeded starting scatter.

    `rules` is a square table (`random_rules`, or hand-made) whose size is the
    number of species; `count` particles are dealt round-robin among them over
    a `size` = (w, h) field, edges wrapping when `wrap` (else bouncing).
    `radius` is how far a particle feels others, in px; `strength` scales every
    force; `friction` is the share of velocity kept per step. Pure Python with
    a grid of radius-sized cells, so a few hundred particles over ~100 steps
    run in about a second; the result is cached, so a film can call it from
    its draw function every frame."""
    w, h = size
    k = len(rules)
    rnd = random.Random(f'life:{seed}')
    xs = [rnd.uniform(0, w) for _ in range(count)]
    ys = [rnd.uniform(0, h) for _ in range(count)]
    kind = [i % k for i in range(count)]
    vx, vy = [0.0] * count, [0.0] * count
    cols, rows = max(1, int(w // radius)), max(1, int(h // radius))
    cw, ch = w / cols, h / rows
    frames = [tuple(zip(xs, ys, kind))]
    for _ in range(steps):
        grid = {}
        for i in range(count):
            grid.setdefault((int(xs[i] // cw) % cols, int(ys[i] // ch) % rows), []).append(i)
        for i in range(count):
            cx, cy = int(xs[i] // cw) % cols, int(ys[i] // ch) % rows
            row, fx, fy = rules[kind[i]], 0.0, 0.0
            seen = set()
            for gx in (cx - 1, cx, cx + 1):
                for gy in (cy - 1, cy, cy + 1):
                    cell = (gx % cols, gy % rows) if wrap else (gx, gy)
                    if cell in seen:
                        continue
                    seen.add(cell)
                    for j in grid.get(cell, ()):
                        if j == i:
                            continue
                        dx, dy = xs[j] - xs[i], ys[j] - ys[i]
                        if wrap:
                            dx -= w * round(dx / w)
                            dy -= h * round(dy / h)
                        d = math.hypot(dx, dy)
                        if 0 < d < radius:
                            f = life_force(d / radius, row[kind[j]]) / d
                            fx += dx * f
                            fy += dy * f
            vx[i] = vx[i] * friction + fx * strength
            vy[i] = vy[i] * friction + fy * strength
        for i in range(count):
            x, y = xs[i] + vx[i], ys[i] + vy[i]
            if wrap:
                x, y = x % w, y % h
            else:
                if not 0 <= x <= w:
                    vx[i], x = -vx[i], min(max(x, 0), w)
                if not 0 <= y <= h:
                    vy[i], y = -vy[i], min(max(y, 0), h)
            xs[i], ys[i] = x, y
        frames.append(tuple(zip(xs, ys, kind)))
    return tuple(frames)


def draw_life(cv, frame, colors, r=4.0, x=0.0, y=0.0, alpha=1.0):
    """Draw one `particle_life` frame as dots, species `s` in `colors[s]`,
    offset by (x, y)."""
    for px, py, s in frame:
        demo.dot(cv, x + px, y + py, r, color=colors[s % len(colors)], alpha=alpha)


COLORS = (demo.ACCENT, demo.TEAL, demo.INK, '#f2c14e')
# Each colour likes its own kind; red chases teal, teal flees red, gold trails white:
# clumps form, then drift and pair off instead of freezing.
RULES = ((0.9, 0.6, -0.3, -0.2),
         (-0.5, 0.8, 0.3, -0.2),
         (-0.2, 0.2, 0.7, 0.4),
         (0.1, -0.3, 0.6, 0.9))
COUNT = 320


def draw(n, cv):
    frames = particle_life(RULES, COUNT, (demo.W, demo.H), round(demo.SECONDS * demo.FPS), seed=4)
    draw_life(cv, frames[min(n, len(frames) - 1)], COLORS)
    cv.mark('field', 0, 0, demo.W, demo.H)


CAPABILITY = Capability(
    id='particle-life',
    name='Particle Life',
    family='particles',
    group='Swarms & agents',
    aliases=('attraction matrix particles', 'species rule particles', 'artificial life particles',
             'primordial particle system'),
    definition='Dots of a few colours each follow a simple table saying which colours they move toward and '
               'which they back away from, and an even scatter organises itself into clumps, chases and rings.',
    phrasings=('coloured particles that clump together like living cells',
               'a little artificial-life simulation where dots attract and repel each other by colour',
               'random dots that self-organise into blobs that chase each other'),
    related=('animated-sprite-particles', 'gravity-well-attraction', 'conway-s-game-of-life',
             'particle-swarm-assemble', 'reaction-diffusion', 'particle-morph'),
    api=('videobuilder.capabilities.particles.particle_life.particle_life',
         'videobuilder.capabilities.particles.particle_life.draw_life',
         'videobuilder.capabilities.particles.particle_life.random_rules',
         'videobuilder.capabilities.particles.particle_life.life_force'),
    demo=lambda: demo.film(draw),
)
