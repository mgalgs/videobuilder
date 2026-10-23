"""Predator avoidance flock: a school of little arrowheads swims together
until a hunter cuts through it; the ones nearest bolt away, the school splits
apart around the hunter's path, then closes back up once it has gone by."""
import math
import random

from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Capability


def simulate(predator, frames, home, count=90, fps=30, seed=0, spawn=140, speed=200, max_speed=600,
             sight=150, crowd=26, fear=260, panic=5200, home_pull=5.0, substeps=2):
    """Run a flock for `frames` frames and return, per frame, a list of
    `(x, y, vx, vy)` for every member. Each member steers by the usual three
    flocking rules -- keep apart within `crowd` px, match heading and drift
    to the middle of the others within `sight` px -- plus a pull toward
    `home(t)` (an (x, y) for time `t` in seconds) so the school regroups, and
    a flee force that grows sharply inside `fear` px of `predator(t)` (an
    (x, y), or None while there is no predator). `panic` scales the flee;
    members cruise near `speed` and may sprint to `max_speed` px/s. They start
    in a disc of radius `spawn` about `home(0)`. Deterministic for a `seed`;
    simulate once and index the result per frame."""
    rnd = random.Random(f'flock:{seed}')
    hx, hy = home(0)
    boids = []
    for _ in range(count):
        a, r = rnd.uniform(0, 2 * math.pi), spawn * math.sqrt(rnd.random())
        h = rnd.uniform(0, 2 * math.pi)
        boids.append([hx + r * math.cos(a), hy + r * math.sin(a), speed * math.cos(h), speed * math.sin(h)])
    dt = 1 / (fps * substeps)
    out = [[tuple(b) for b in boids]]
    for f in range(1, frames):
        for s in range(substeps):
            t = (f - 1 + s / substeps) / fps
            hx, hy = home(t)
            pred = predator(t)
            acc = []
            for i, (x, y, vx, vy) in enumerate(boids):
                ax = ay = 0.0
                cx = cy = mvx = mvy = 0.0
                seen = 0
                for j, (ox, oy, ovx, ovy) in enumerate(boids):
                    if i == j:
                        continue
                    dx, dy = x - ox, y - oy
                    d2 = dx * dx + dy * dy
                    if d2 < sight * sight:
                        seen += 1
                        cx, cy, mvx, mvy = cx + ox, cy + oy, mvx + ovx, mvy + ovy
                        if d2 < crowd * crowd:
                            d = math.sqrt(d2) or 1e-3
                            push = (crowd - d) / crowd * 2400
                            ax, ay = ax + dx / d * push, ay + dy / d * push
                if seen:
                    ax += (cx / seen - x) * 2.0 + (mvx / seen - vx) * 1.6
                    ay += (cy / seen - y) * 2.0 + (mvy / seen - vy) * 1.6
                calm = 1.0
                if pred is not None:
                    dx, dy = x - pred[0], y - pred[1]
                    d = math.hypot(dx, dy) or 1e-3
                    if d < fear:
                        k = (1 - d / fear) ** 2
                        ax, ay = ax + dx / d * panic * k, ay + dy / d * panic * k
                        calm = 1 - k
                pull = home_pull * calm   # a fleeing member forgets home until it is safe
                ax, ay = ax - vx * 1.2 * calm, ay - vy * 1.2 * calm   # settling, so the school does not overshoot
                ax += (hx - x) * pull + (-(y - hy)) * 0.9 * calm   # and the school slowly circles it
                ay += (hy - y) * pull + (x - hx) * 0.9 * calm
                acc.append((ax, ay))
            for b, (ax, ay) in zip(boids, acc):
                b[2] += ax * dt
                b[3] += ay * dt
                v = math.hypot(b[2], b[3]) or 1e-3
                want = min(max_speed, max(speed * 0.6, v))
                b[2], b[3] = b[2] / v * want, b[3] / v * want
                b[2] += (b[2] / want * speed - b[2]) * 0.8 * dt  # ease back to cruising speed
                b[3] += (b[3] / want * speed - b[3]) * 0.8 * dt
                b[0] += b[2] * dt
                b[1] += b[3] * dt
        out.append([tuple(b) for b in boids])
    return out


def draw_flock(cv, members, color=demo.TEAL, size=14, alpha=1.0):
    """Draw one frame of `simulate()` output: each member a small arrowhead
    pointing along its velocity, `size` px long."""
    c = cv.ctx
    c.set_source_rgba(*rgba(color, alpha))
    for x, y, vx, vy in members:
        v = math.hypot(vx, vy) or 1e-3
        ux, uy = vx / v, vy / v
        c.move_to(x + ux * size * 0.6, y + uy * size * 0.6)
        c.line_to(x - ux * size * 0.4 - uy * size * 0.32, y - uy * size * 0.4 + ux * size * 0.32)
        c.line_to(x - ux * size * 0.2, y - uy * size * 0.2)
        c.line_to(x - ux * size * 0.4 + uy * size * 0.32, y - uy * size * 0.4 - ux * size * 0.32)
        c.close_path()
    c.fill()


FRAMES = round(demo.SECONDS * demo.FPS)
HOME = (demo.W * 0.5, demo.H * 0.5)
PREDATOR_R = 46


def _predator(t):
    """The hunter sweeps in from the left, slows as it ploughs through the
    school (so it is still among the parted members at the poster frame, 2.1 s),
    then darts out the right by about 2.5 s, leaving the rest for the regroup."""
    p = (t - 0.8) / 1.75
    if not 0 <= p <= 1:
        return None
    s = p + 0.8 * math.sin(2 * math.pi * p) / (2 * math.pi)   # fast at the edges, slow in the middle
    return -120 + (demo.W + 240) * s, demo.H * 0.5 + 30 * math.sin(p * math.pi * 1.2)


_RUN = []


def _run():
    if not _RUN:
        _RUN.append(simulate(_predator, FRAMES, lambda t: HOME, count=110, seed=4, fear=220, panic=3500,
                             home_pull=7.0))
    return _RUN[0]


def draw(n, cv):
    draw_flock(cv, _run()[n], demo.TEAL, size=18)
    pred = _predator(n / demo.FPS)
    if pred is not None:
        demo.dot(cv, pred[0], pred[1], PREDATOR_R, demo.ACCENT)
        cv.mark('predator', pred[0] - PREDATOR_R, pred[1] - PREDATOR_R, 2 * PREDATOR_R, 2 * PREDATOR_R)


CAPABILITY = Capability(
    id='predator-avoidance-flock',
    name='Predator avoidance flock',
    family='particles',
    group='Swarms & agents',
    aliases=('flee behavior', 'scatter response', 'boids with predator'),
    definition='A swarm of small moving agents parts and races away from a hunter passing through it, '
               'then drifts back together once the hunter has gone.',
    phrasings=('a school of fish that splits apart when a shark swims through',
               'make the swarm scatter from the big dot and then regroup',
               'birds flocking that dodge a hawk flying past'),
    related=('fireflies', 'random-stagger', 'dashed-line-march', 'doom-style-fire', 'spotlight-follow',
             'force-directed-network-settle'),
    api=('videobuilder.capabilities.particles.predator_avoidance_flock.simulate',
         'videobuilder.capabilities.particles.predator_avoidance_flock.draw_flock'),
    demo=lambda: demo.film(draw),
)
