"""Proximity Stagger: a group of items reacts to a trigger point one after
another, each starting later the farther it sits from that point, so the
change spreads outward like a ring on water."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

# A pointer arrow, tip at (0, 0), in pixels at scale 1.
ARROW = ((0, 0), (0, 27), (7, 21), (12, 32), (17.5, 29.5), (12.5, 19), (21, 19))


def proximity_delays(points, origin, spread=0.6, reach=None):
    """For each `(x, y)` in `points`, its start delay as a fraction of the
    whole move: 0 at `origin`, rising in proportion to distance, to `spread`
    at `reach` pixels (default: the farthest point). Points beyond `reach`
    wait `spread`."""
    ox, oy = origin
    dists = [math.hypot(x - ox, y - oy) for x, y in points]
    reach = reach or max(dists, default=0) or 1.0
    return [spread * min(d / reach, 1.0) for d in dists]


def proximity_stagger(points, origin, p, spread=0.6, reach=None, ease=vb.linear):
    """Each item's own progress at overall progress `p` (0 -> 1): items start
    in order of distance from `origin` (see `proximity_delays`) and each runs
    for the remaining `1 - spread` of the move, so the farthest ends at
    `p = 1`. `ease` shapes each item's progress."""
    span = max(1.0 - spread, 1e-6)
    return [ease(vb.clamp01((p - d) / span)) for d in proximity_delays(points, origin, spread, reach)]


def _arrow(cv, x, y, s=1.0):
    pts = [(x + px * s, y + py * s) for px, py in ARROW]
    cv.shape_shadow(pts, dx=2, dy=4, blur=6, color=(0, 0, 0, 0.45))
    ctx = cv.ctx
    ctx.new_path()
    ctx.move_to(*pts[0])
    for pt in pts[1:]:
        ctx.line_to(*pt)
    ctx.close_path()
    ctx.set_source_rgba(*vb.rgba(demo.INK))
    ctx.fill_preserve()
    ctx.set_source_rgba(*vb.rgba(demo.BG))
    ctx.set_line_width(2)
    ctx.stroke()


COLS, ROWS, GAP = 11, 6, 72
GRID = [(demo.W / 2 + (c - (COLS - 1) / 2) * GAP, demo.H / 2 + (r - (ROWS - 1) / 2) * GAP)
        for r in range(ROWS) for c in range(COLS)]
TARGET = GRID[2 * COLS + 3]  # off-centre, so the wave has near and far sides
CLICK = 0.8                  # seconds


def draw(n, cv):
    t = n / demo.FPS
    tx, ty = TARGET[0] + 10, TARGET[1] + 10
    origin = (tx, ty)
    for (x, y), q in zip(GRID, proximity_stagger(GRID, origin, demo.phase(n, CLICK, 2.6), spread=0.75)):
        r = 11 + 9 * vb.ease_out_back(q)
        demo.dot(cv, x, y, r, color=demo.TEAL if q <= 0 else demo.kit.mix(demo.TEAL, demo.ACCENT, min(q * 2, 1)))
    # The click: a faint ring leaving the trigger point.
    ring = demo.phase(n, CLICK, CLICK + 0.7)
    if 0 < ring < 1:
        cv.arc(tx, ty, 10 + 70 * ring, 0, 2 * math.pi, demo.INK, width=3, alpha=0.6 * (1 - ring))
    # The pointer glides in from the lower right, presses, and stays.
    arrive = vb.ease_out_expo(demo.phase(n, 0.0, CLICK - 0.1))
    sx, sy = demo.W + 40, demo.H + 40
    press = 1 - 0.15 * math.sin(math.pi * vb.clamp01((t - CLICK + 0.05) / 0.2))
    _arrow(cv, sx + (tx - sx) * arrive, sy + (ty - sy) * arrive, 1.3 * press)
    cv.mark('pointer', tx, ty, 28, 42)


TECHNIQUE = Technique(
    id='proximity-stagger',
    name='Proximity Stagger',
    family='principles',
    group='Stagger',
    aliases=('pointer stagger', 'distance-based delay', 'cursor ripple'),
    definition='A set of items each starts its move after a delay that grows with its distance from a '
               'chosen point, so the change washes outward from there.',
    phrasings=('the dots light up starting where I click and spread outwards',
               'stagger them by how far they are from the cursor',
               'make the grid react in a ripple out from one spot'),
    related=('cursor-follower-dot-and-ring', 'linear-repeater-stagger', 'cursor-path-animation',
             'per-word-fade-in', 'cursor-state-change', 'cursor-particle-trail'),
    api=('videobuilder.techniques.principles.proximity_stagger.proximity_stagger',
         'videobuilder.techniques.principles.proximity_stagger.proximity_delays'),
    demo=lambda: demo.film(draw),
)
