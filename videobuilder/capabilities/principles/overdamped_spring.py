"""Overdamped Spring: videobuilder already has it as `vb.spring` with params
from `vb.damped(ratio)` at a ratio above 1, so this entry only names it and
demos it."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

PARAMS = vb.damped(3.0, hz=1.2)  # ratio 3: heavy damping, a slow creep with no overshoot
START, END = 0.3, demo.SECONDS


def _coil(cv, x0, x1, y, turns=12, amp=11):
    """A zigzag spring from x0 to x1 at height y."""
    lead = 12
    pts = [(x0, y), (x0 + lead, y)]
    step = (x1 - x0 - 2 * lead) / (2 * turns)
    for i in range(1, 2 * turns):
        pts.append((x0 + lead + i * step, y + (amp if i % 2 else -amp)))
    pts += [(x1 - lead, y), (x1, y)]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        cv.line(ax, ay, bx, by, demo.TEAL, width=3)


def draw(n, cv):
    y, r = 180, 36
    wall, x0, x1 = 120, 220, 800
    x = x0 + (x1 - x0) * vb.spring(n / demo.FPS - START, **PARAMS)
    cv.line(wall, y - 56, wall, y + 56, demo.INK, width=6)
    cv.arc(x1, y, r + 6, 0, 6.2832, demo.MUTED, width=3, alpha=0.6)  # where it comes to rest
    cv.line(x1, y - r - 24, x1, y + r + 24, demo.MUTED, width=2, alpha=0.6)
    _coil(cv, wall, x - r, y)
    demo.dot(cv, x, y, r)
    cv.mark('ball', x - r, y - r, 2 * r, 2 * r)

    # Position over time: the curve rises and flattens onto the target line without crossing it.
    gx, gy, gw, gh = wall, demo.H - 180, x1 - wall, 110
    cv.line(gx, gy + gh, gx + gw, gy + gh, demo.LINE, width=2)
    cv.line(gx, gy, gx + gw, gy, demo.MUTED, width=2, alpha=0.6)
    prev = None
    for i in range(n + 1):
        t = i / demo.FPS
        pt = (gx + gw * t / END, gy + gh - gh * vb.spring(t - START, **PARAMS))
        if prev:
            cv.line(*prev, *pt, demo.ACCENT, width=3)
        prev = pt
    if prev:
        demo.dot(cv, prev[0], prev[1], 6)
    demo.word(cv, 'no overshoot', gx + gw - 80, gy - 20, size=20, color=demo.MUTED, weight=600)


CAPABILITY = Capability(
    id='overdamped-spring',
    name='Overdamped Spring',
    family='principles',
    group='Physics',
    aliases=('sluggish spring', 'heavily damped spring', 'overdamped ease'),
    definition='A spring so heavily damped that it drifts toward its target and slowly settles there, '
               'never passing it or bouncing back.',
    phrasings=('glides in slowly and settles without any bounce',
               'a lazy spring that just creeps into place',
               'springy but heavy, with no overshoot at all'),
    related=('overshoot-bounce-in', 'spring-return', 'springs-network', 'spring-drag-letters',
             'elastic-ease-out', 'mass-spring-cloth'),
    api=('videobuilder.spring', 'videobuilder.damped'),
    demo=lambda: demo.film(draw),
)
