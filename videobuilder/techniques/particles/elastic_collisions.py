"""Elastic collisions: balls in a box that bounce off the walls and off each
other with no energy lost, heavier balls shoving lighter ones aside the way
billiard balls do."""
import math
from functools import lru_cache

from .. import _demo as demo
from ..schema import Technique


def elastic_collisions(balls, box, frames, fps=30, substeps=8):
    """Simulate `balls` bouncing inside `box` with perfectly elastic
    collisions, and return `(paths, hits)`.

    `balls` is a sequence of `(x, y, vx, vy, r)` (pixels, pixels per second);
    each ball's mass goes with its area, so big balls push small ones. `box`
    is `(x, y, w, h)`: the walls the balls rebound from. `paths[n][i]` is
    ball `i`'s `(x, y)` at frame `n`, for `frames` frames at `fps`; `hits` is
    a list of `(n, x, y)`, one per ball-on-ball contact, at the contact
    point. Deterministic, so a film can call it once and index any frame.
    """
    bx, by, bw, bh = box
    state = [list(b) for b in balls]
    mass = [b[4] * b[4] for b in state]
    dt = 1 / (fps * substeps)
    paths, hits = [], []
    for n in range(frames):
        paths.append(tuple((b[0], b[1]) for b in state))
        for _ in range(substeps):
            for b in state:
                b[0] += b[2] * dt
                b[1] += b[3] * dt
                x, y, r = b[0], b[1], b[4]
                if x - r < bx and b[2] < 0 or x + r > bx + bw and b[2] > 0:
                    b[2] = -b[2]
                if y - r < by and b[3] < 0 or y + r > by + bh and b[3] > 0:
                    b[3] = -b[3]
            for i in range(len(state)):
                for j in range(i + 1, len(state)):
                    if _collide(state[i], state[j], mass[i], mass[j]):
                        a, b = state[i], state[j]
                        k = a[4] / (a[4] + b[4])
                        hits.append((n, a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k))
    return paths, hits


def _collide(a, b, ma, mb):
    """Resolve one ball-ball contact in place; True if they hit. Exchanges
    velocity along the line of centres (keeping momentum and kinetic energy)
    and pushes the pair apart so they don't stick."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    d = math.hypot(dx, dy)
    reach = a[4] + b[4]
    if d >= reach or d == 0:
        return False
    nx, ny = dx / d, dy / d
    closing = (a[2] - b[2]) * nx + (a[3] - b[3]) * ny
    push = (reach - d) / 2
    a[0] -= nx * push
    a[1] -= ny * push
    b[0] += nx * push
    b[1] += ny * push
    if closing <= 0:
        return False  # already separating
    impulse = 2 * closing / (ma + mb)
    a[2] -= impulse * mb * nx
    a[3] -= impulse * mb * ny
    b[2] += impulse * ma * nx
    b[3] += impulse * ma * ny
    return True


BOX = (demo.W / 2 - 400, demo.H / 2 - 210, 800, 420)
BALLS = (  # (x, y, vx, vy, r), aimed so the first contacts come early
    (BOX[0] + 140, BOX[1] + 120, 330, 90, 40),
    (BOX[0] + 400, BOX[1] + 210, -170, -30, 28),
    (BOX[0] + 640, BOX[1] + 110, -310, 170, 32),
    (BOX[0] + 180, BOX[1] + 320, 250, -200, 24),
    (BOX[0] + 590, BOX[1] + 330, -130, -270, 36),
    (BOX[0] + 370, BOX[1] + 60, 80, 250, 22),
)
COLORS = (demo.ACCENT, demo.TEAL, demo.ACCENT, demo.TEAL, demo.ACCENT, demo.TEAL)
FLASH = 6  # frames a contact ring lasts


@lru_cache(maxsize=1)
def _sim():
    return elastic_collisions(BALLS, BOX, round(demo.SECONDS * demo.FPS), demo.FPS)


def draw(n, cv):
    paths, hits = _sim()
    cv.outline(*BOX, demo.MUTED, width=3, radius=6, alpha=0.6)
    for hn, x, y in hits:
        age = n - hn
        if 0 <= age < FLASH:
            t = age / FLASH
            cv.outline(x - 8 - 24 * t, y - 8 - 24 * t, 16 + 48 * t, 16 + 48 * t, demo.INK,
                       width=2, radius=8 + 24 * t, alpha=0.8 * (1 - t))
    for i, ((x, y), ball) in enumerate(zip(paths[n], BALLS)):
        r = ball[4]
        demo.dot(cv, x, y, r, color=COLORS[i])
        cv.mark(f'ball{i}', x - r, y - r, 2 * r, 2 * r)


TECHNIQUE = Technique(
    id='elastic-collisions',
    name='Elastic collisions',
    family='particles',
    group='Forces',
    aliases=('ball-ball collision', 'billiard particles', 'text collision bounce', 'word ball collision'),
    definition='Balls ricochet off the walls and off one another without ever slowing down, '
               'big ones knocking small ones away as if they were billiard balls.',
    phrasings=('balls bouncing around a box and knocking into each other',
               'dots that ping off one another like pool balls',
               'make the circles collide and bounce apart'),
    related=('impact', 'ball-bounce', 'newton-s-cradle', 'physics-letter-drop', 'overlapping-action',
             'n-body-gravity'),
    api=('videobuilder.techniques.particles.elastic_collisions.elastic_collisions',),
    demo=lambda: demo.film(draw),
)
