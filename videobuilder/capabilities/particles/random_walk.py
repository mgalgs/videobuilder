"""Random Walk: a point takes one short step in a random direction after
another, and the jagged trail it leaves behind meanders, doubles back on
itself and slowly fills in a patch of the frame."""
import math
import random
from functools import lru_cache

from .. import _demo as demo
from ..schema import Capability


def random_walk(count, seed=0, step=10.0, start=(0.0, 0.0), bounds=None, jitter=0.5):
    """`count + 1` points of a random walk from `start`: each step goes
    `step` px (varied by up to +-`jitter` of itself) in a uniformly random
    direction. `bounds` (x0, y0, x1, y1) reflects any step that would leave
    the box back inside it, so the walk stays in frame. Deterministic for a
    given `seed`; reveal the first `k` points over time to animate it."""
    rnd = random.Random(f'random-walk:{seed}')
    x, y = start
    pts = [(x, y)]
    for _ in range(count):
        a = rnd.uniform(0, 2 * math.pi)
        d = step * (1 + rnd.uniform(-jitter, jitter))
        x, y = x + d * math.cos(a), y + d * math.sin(a)
        if bounds:
            x0, y0, x1, y1 = bounds
            x = 2 * x0 - x if x < x0 else 2 * x1 - x if x > x1 else x
            y = 2 * y0 - y if y < y0 else 2 * y1 - y if y > y1 else y
        pts.append((x, y))
    return pts


def draw_walk(cv, pts, color, head_color=None, width=3, fresh=24, fresh_color=None, alpha=0.75):
    """Draw a walk's trail: every segment in `color`, the newest `fresh`
    segments in `fresh_color` so the direction of travel reads, and a dot in
    `head_color` at the end of the walk (omit it for no dot)."""
    last = len(pts) - 1
    for i in range(last):
        (ax, ay), (bx, by) = pts[i], pts[i + 1]
        if fresh_color and i >= last - fresh:
            cv.line(ax, ay, bx, by, fresh_color, width=width + 1)
        else:
            cv.line(ax, ay, bx, by, color, width=width, alpha=alpha)
    if head_color and pts:
        demo.dot(cv, pts[-1][0], pts[-1][1], 11, color=head_color)


STEPS = 1400


@lru_cache(maxsize=None)
def _walk():
    # seed 6 wanders over a wide patch without touching the bounds; the start is
    # offset so that patch sits centred in the frame
    return random_walk(STEPS, seed=6, step=9, start=(demo.W / 2 - 216, demo.H / 2 - 50),
                       bounds=(40, 40, demo.W - 40, demo.H - 40))


def draw(n, cv):
    p = demo.phase(n, 0, demo.SECONDS - 0.15)
    k = min(STEPS, 12 + round(STEPS * p ** 1.3))  # starts slow so the first steps read, then speeds up to fill
    draw_walk(cv, _walk()[:k + 1], demo.TEAL, head_color=demo.ACCENT, fresh_color=demo.INK)


CAPABILITY = Capability(
    id='random-walk',
    name='Random walk',
    family='particles',
    group='Interaction fields',
    aliases=('Brownian motion', "drunkard's walk", 'random path', 'brownian walk'),
    definition='A dot hops in a fresh random direction every moment, scribbling a tangled, '
               'zig-zag trail that wanders off and gradually fills a region of the screen.',
    phrasings=('have a dot stumble around randomly and leave a scribbly line behind it',
               'show a jittery wandering path like a particle bouncing around under a microscope',
               'animate a line that keeps taking random little steps until it covers the area'),
    related=('wander-steering', 'diffusion-limited-aggregation', 'path-emitter', 'cursor-particle-trail',
             'walk-cycle', 'player-movement-trail'),
    api=('videobuilder.capabilities.particles.random_walk.random_walk',
         'videobuilder.capabilities.particles.random_walk.draw_walk'),
    demo=lambda: demo.film(draw),
)
