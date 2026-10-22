"""Boids flocking: many small arrow-shaped agents, each steering only by its
near neighbours (keep apart, match heading, close in), pull themselves out of
a scattered muddle into one flock that wheels across the frame together."""
import functools
import math
import random

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Capability


@functools.lru_cache(maxsize=8)
def flock(count, steps, bounds, seed=0, radius=110.0, spacing=34.0, speed=7.0, separation=1.6,
          alignment=0.9, cohesion=0.55, margin=120.0, goal=None, goal_pull=0.25):
    """Simulate a boids flock and return its state at every step: a tuple of
    `steps + 1` frames, each a tuple of `(x, y, vx, vy)` per boid.

    Boids start at seeded random spots inside `bounds` (x, y, w, h) with random
    headings. Each step every boid looks at the others within `radius` px and
    steers by three rules: away from any closer than `spacing` (`separation`),
    towards their average heading (`alignment`) and towards their centre
    (`cohesion`). Near the edges (within `margin`) it turns back in, and if
    `goal(i)` is given (step -> (x, y)) the whole flock leans towards that
    point by `goal_pull`. Speed stays near `speed` px per step. The same
    arguments give the same flock, so a film can index it by frame number; the
    result is cached, so call it from `draw` freely (pass `goal` as a
    module-level function so it hashes the same every time)."""
    bx, by, bw, bh = bounds
    rnd = random.Random(f'boids:{seed}')
    boids = []
    for _ in range(count):
        a = rnd.uniform(0, 2 * math.pi)
        boids.append([bx + rnd.random() * bw, by + rnd.random() * bh, speed * math.cos(a), speed * math.sin(a)])
    out = [tuple(tuple(b) for b in boids)]
    r2, s2 = radius * radius, spacing * spacing
    for i in range(steps):
        gx, gy = goal(i) if goal else (None, None)
        new = []
        for j, (x, y, vx, vy) in enumerate(boids):
            sx = sy = ax = ay = cx = cy = 0.0
            seen = 0
            for k, (ox, oy, ovx, ovy) in enumerate(boids):
                if k == j:
                    continue
                dx, dy = ox - x, oy - y
                d2 = dx * dx + dy * dy
                if d2 > r2:
                    continue
                seen += 1
                ax += ovx
                ay += ovy
                cx += dx
                cy += dy
                if d2 < s2:
                    f = (1 - math.sqrt(d2) / spacing) / max(math.sqrt(d2), 1.0)
                    sx -= dx * f
                    sy -= dy * f
            fx, fy = sx * separation * speed, sy * separation * speed
            if seen:
                fx += (ax / seen - vx) * alignment * 0.12 + cx / seen * cohesion * 0.01
                fy += (ay / seen - vy) * alignment * 0.12 + cy / seen * cohesion * 0.01
            if gx is not None:
                dx, dy = gx - x, gy - y
                d = max(math.hypot(dx, dy), 1.0)
                fx += dx / d * goal_pull
                fy += dy / d * goal_pull
            turn = 0.6
            if x < bx + margin:
                fx += turn * (1 - (x - bx) / margin)
            if x > bx + bw - margin:
                fx -= turn * (1 - (bx + bw - x) / margin)
            if y < by + margin:
                fy += turn * (1 - (y - by) / margin)
            if y > by + bh - margin:
                fy -= turn * (1 - (by + bh - y) / margin)
            vx, vy = vx + fx, vy + fy
            v = max(math.hypot(vx, vy), 1e-6)
            k = min(max(v, speed * 0.7), speed * 1.3) / v
            new.append([x, y, vx * k, vy * k])
        for b in new:
            b[0] += b[2]
            b[1] += b[3]
        boids = new
        out.append(tuple(tuple(b) for b in boids))
    return tuple(out)


def draw_boid(cv, x, y, vx, vy, size=14.0, color=demo.INK, alpha=1.0):
    """One boid at (x, y): a slim arrowhead `size` px long pointing along (vx, vy)."""
    v = max(math.hypot(vx, vy), 1e-6)
    ux, uy = vx / v, vy / v
    px, py = -uy, ux
    pts = [(x + ux * size * 0.6, y + uy * size * 0.6),
           (x - ux * size * 0.4 + px * size * 0.35, y - uy * size * 0.4 + py * size * 0.35),
           (x - ux * size * 0.2, y - uy * size * 0.2),
           (x - ux * size * 0.4 - px * size * 0.35, y - uy * size * 0.4 - py * size * 0.35)]
    c = cv.ctx
    c.new_path()
    c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    c.close_path()
    c.set_source_rgba(*rgba(color, alpha))
    c.fill()


def draw_flock(cv, frames, step, size=14.0, colors=(demo.INK,), trail=6, trail_color=None, seed=0):
    """Draw step `step` of a flock from `flock(...)`: each boid as an arrowhead
    in one of `colors` (picked by seed), behind it a fading line through its
    last `trail` positions. Returns the Box around the flock."""
    step = max(0, min(step, len(frames) - 1))
    rnd = random.Random(f'boid-colors:{seed}')
    cols = [rnd.choice(colors) for _ in frames[step]]
    for i, col in enumerate(cols):
        for t in range(max(0, step - trail), step):
            (x0, y0, _, _), (x1, y1, _, _) = frames[t][i], frames[t + 1][i]
            age = (step - t) / (trail + 1)
            cv.line(x0, y0, x1, y1, trail_color or col, width=2, alpha=0.35 * (1 - age))
    for (x, y, vx, vy), col in zip(frames[step], cols):
        draw_boid(cv, x, y, vx, vy, size, col)
    xs, ys = [b[0] for b in frames[step]], [b[1] for b in frames[step]]
    return vb.Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


STEPS = round(demo.SECONDS * demo.FPS)
BOUNDS = (60, 60, demo.W - 120, demo.H - 120)


def _goal(i):
    """A slow loop around the frame centre for the demo flock to chase."""
    a = -math.pi / 2 + 2 * math.pi * i / (STEPS * 1.1)
    return demo.W / 2 + 520 * math.cos(a), demo.H / 2 + 260 * math.sin(a)


def _frames():
    return flock(110, STEPS, BOUNDS, seed=4, goal=_goal)


def draw(n, cv):
    box = draw_flock(cv, _frames(), n, size=18, colors=(demo.INK, demo.INK, demo.ACCENT, demo.TEAL), seed=4)
    cv.mark('flock', *box)


CAPABILITY = Capability(
    id='boids-flocking',
    name='Boids flocking',
    family='particles',
    group='Swarms & agents',
    aliases=('boids', 'flocking simulation', 'flock of birds', 'schooling fish', 'swarm behaviour'),
    definition='A crowd of small pointed agents, each reacting only to the ones nearest it, '
               'sorts itself from a jumble into a single flock that turns and travels as one.',
    phrasings=('little arrows that start scattered and then flock together like birds',
               'a school of fish swimming around the screen as a group',
               'make the particles swarm and move together like a murmuration'),
    related=('rigid-body-pile', 'bokeh-particles', 'k-rm-n-vortex-street', 'card-deck-fan',
             'particle-swarm-assemble', 'random-stagger'),
    api=('videobuilder.capabilities.particles.boids_flocking.flock',
         'videobuilder.capabilities.particles.boids_flocking.draw_flock',
         'videobuilder.capabilities.particles.boids_flocking.draw_boid'),
    demo=lambda: demo.film(draw),
)
