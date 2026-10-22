"""Ease Out Circ: an easing curve shaped like a quarter circle, so a move
leaves at a near-vertical speed, loses most of it at once, and spends the
rest of its time drifting softly onto the target."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def ease_out_circ(x):
    """Progress `x` in [0, 1] -> eased progress along a quarter circle,
    sqrt(1 - (1 - x)^2): infinitely steep at the start, flat at the end."""
    x = vb.clamp01(x)
    return math.sqrt(1 - (1 - x) ** 2)


START, END = 0.5, 2.3
TICKS = 12  # equal slices of time; their marks bunch up as the move slows


def draw(n, cv):
    p = demo.phase(n, START, END)
    r, y = 26, 130
    x0, x1 = demo.W / 2 - 340, demo.W / 2 + 340
    demo.floor(cv, y + r + 16, color=demo.LINE)
    cv.arc(x0, y, r, 0, 2 * math.pi, demo.MUTED, width=2, alpha=0.5)
    cv.arc(x1, y, r, 0, 2 * math.pi, demo.MUTED, width=2, alpha=0.5)
    for i in range(1, TICKS):  # where the ball was at each equal step of time
        if i / TICKS <= p:
            tx = x0 + (x1 - x0) * ease_out_circ(i / TICKS)
            cv.line(tx, y + r + 6, tx, y + r + 26, demo.ACCENT, width=3, alpha=0.8)
    bx = x0 + (x1 - x0) * ease_out_circ(p)
    demo.dot(cv, bx, y, r)
    cv.mark('ball', bx - r, y - r, 2 * r, 2 * r)

    # The curve itself, traced as time runs: time across, progress up.
    gw, gh = 380, 230
    gx, gy = demo.W / 2 - gw / 2, demo.H - 50 - gh
    cv.outline(gx, gy, gw, gh, demo.LINE, width=2, alpha=0.6)
    steps = 120
    pts = [(gx + gw * i / steps, gy + gh * (1 - ease_out_circ(i / steps))) for i in range(steps + 1)]
    for (ax, ay), (bx2, by2) in zip(pts, pts[1:]):
        cv.line(ax, ay, bx2, by2, demo.MUTED, width=2, alpha=0.5)
    done = [pt for i, pt in enumerate(pts) if i / steps <= p]
    for (ax, ay), (bx2, by2) in zip(done, done[1:]):
        cv.line(ax, ay, bx2, by2, demo.TEAL, width=3)
    hx, hy = gx + gw * p, gy + gh * (1 - ease_out_circ(p))
    cv.line(hx, gy + gh, hx, hy, demo.MUTED, width=1, alpha=0.6)
    demo.dot(cv, hx, hy, 6, color=demo.INK)


TECHNIQUE = Technique(
    id='ease-out-circ',
    name='Ease Out Circ',
    family='principles',
    group='Easing',
    aliases=('easeOutCirc', 'circular out', 'circ out'),
    definition='A move that launches almost instantly at top speed, loses most of that speed right away, '
               'and then coasts slowly and smoothly into its final spot.',
    phrasings=('shoots off fast and then gently drifts to a stop',
               'whips out quickly and glides the rest of the way in',
               'a very sudden start that softly settles at the end'),
    related=('slow-in-and-slow-out', 'settle', 'momentum-fling', 'dolly-in-and-out', 'follow-through',
             'smooth-scroll-inertia'),
    api=('videobuilder.techniques.principles.ease_out_circ.ease_out_circ',),
    demo=lambda: demo.film(draw),
)
