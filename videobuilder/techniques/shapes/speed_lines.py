"""Speed lines: a bundle of parallel strokes trailing behind something that
moves, long while it is fast, shrinking away as it slows. (Radial speed lines
bursting round a subject are `vb.impact.speed_lines`; these run straight back
along the path of travel.)"""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def trail_lines(cv, x, y, speed, angle=0.0, reach=420, spread=90, gap=40, count=9, seed=0,
                color=demo.INK, width=4, alpha=0.8):
    """Speed lines trailing behind a subject at (x, y) heading `angle`
    radians (0 = moving right, increasing clockwise). `speed` (0 -> 1, more
    stretches further) scales every stroke: at 0 nothing is drawn. Strokes
    start `gap` px behind the subject, run back up to `reach` px, and sit
    within `spread` px either side of the line of travel, the middle ones
    longest. Seeded: the same `seed` draws the same bundle; pass the frame in
    it to make the strokes flicker."""
    if speed <= 0.01:
        return
    rnd = random.Random(seed)
    ux, uy = math.cos(angle), math.sin(angle)       # along the travel
    nx, ny = -uy, ux                                # across it
    for i in range(count):
        off = spread * ((i + rnd.uniform(-0.3, 0.3)) / max(1, count - 1) * 2 - 1)
        centre = 1 - 0.55 * abs(off) / max(1, spread)   # middle strokes reach further
        back0 = gap * rnd.uniform(0.6, 1.6)
        length = reach * speed * centre * rnd.uniform(0.45, 1.0)
        bx, by = x + nx * off, y + ny * off
        cv.line(bx - ux * back0, by - uy * back0, bx - ux * (back0 + length), by - uy * (back0 + length),
                color, width=width * rnd.uniform(0.5, 1.0), alpha=alpha * min(1.0, speed) * rnd.uniform(0.5, 1.0))


def draw(n, cv):
    # A dot dashes in (cubic ease out; its speed is the derivative, 3(1 - p)^2), holds,
    # then dashes off (cubic ease in, speed 3p^2); the strokes follow that speed.
    y, mid, off = demo.H / 2, demo.W / 2, demo.W + 120
    p_in, p_out = demo.phase(n, 0.25, 1.15), demo.phase(n, 1.85, 2.55)
    if p_out > 0:
        x, v = mid + (off - mid) * p_out ** 3, 3 * p_out ** 2
    else:
        x, v = -120 + (mid + 120) * (1 - (1 - p_in) ** 3), 3 * (1 - p_in) ** 2 if p_in > 0 else 0
    s = vb.clamp01(v / 1.5)
    trail_lines(cv, x, y, s, reach=760, spread=120, gap=70, count=11, seed=n // 2, color=demo.ACCENT, width=6,
                alpha=1.0)
    trail_lines(cv, x, y, s, reach=900, spread=300, gap=180, count=8, seed=1000 + n // 2, color=demo.MUTED,
                width=3, alpha=0.6)
    demo.dot(cv, x, y, r=60)
    cv.mark('dot', x - 60, y - 60, 120, 120)


TECHNIQUE = Technique(
    id='speed-lines',
    name='Speed lines',
    family='shapes',
    group='Lines & strokes',
    aliases=('motion lines', 'parallel streaks', 'whoosh lines'),
    definition='Thin straight strokes stream out behind a fast-moving object, growing with its speed '
               'and vanishing when it stops.',
    phrasings=('add those little lines behind it so it looks fast',
               'cartoon whoosh streaks trailing the ball as it zooms in',
               'motion streaks behind the shape while it dashes across'),
    related=('streamlines', 'scanline-jitter', 'speed-ramp', 'line-weave', 'flow-map-lines',
             'parallel-coordinates-draw'),
    api=('videobuilder.techniques.shapes.speed_lines.trail_lines', 'videobuilder.impact.speed_lines'),
    demo=lambda: demo.film(draw),
)
