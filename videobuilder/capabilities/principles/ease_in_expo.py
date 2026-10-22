"""Ease In Expo: videobuilder already has it as `vb.ease_in_expo`, so this
entry only names it and demos it."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

START, END = 0.5, 2.3  # seconds the move runs between


def draw(n, cv):
    p = demo.phase(n, START, END)
    x0, x1, y = 120, demo.W - 120, 150
    cv.line(x0, y + 50, x1, y + 50, demo.LINE, width=3)
    for k in range(n + 1):  # ghosts where the dot was each few frames: bunched at the start, spread at the end
        if k % 3 == 0 and k < n:
            q = vb.ease_in_expo(demo.phase(k, START, END))
            demo.dot(cv, x0 + (x1 - x0) * q, y, 30, color=demo.MUTED, alpha=0.12)
    e = vb.ease_in_expo(p)
    cv.line(x0, y + 50, x0 + (x1 - x0) * e, y + 50, demo.ACCENT, width=4)
    demo.dot(cv, x0 + (x1 - x0) * e, y, 30)
    cv.mark('dot', x0 + (x1 - x0) * e - 30, y - 30, 60, 60)

    gx, gy, gw, gh = demo.W / 2 - 180, 270, 360, 200  # the curve itself, traced as time passes
    cv.line(gx, gy, gx, gy + gh, demo.MUTED, width=2, alpha=0.6)
    cv.line(gx, gy + gh, gx + gw, gy + gh, demo.MUTED, width=2, alpha=0.6)
    steps = 80
    pts = [(gx + gw * i / steps, gy + gh * (1 - vb.ease_in_expo(i / steps))) for i in range(steps + 1)]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        cv.line(ax, ay, bx, by, demo.MUTED, width=2, alpha=0.35)
    done = pts[:round(p * steps) + 1]
    for (ax, ay), (bx, by) in zip(done, done[1:]):
        cv.line(ax, ay, bx, by, demo.ACCENT, width=4)
    demo.dot(cv, gx + gw * p, gy + gh * (1 - e), 7, color=demo.INK)


CAPABILITY = Capability(
    id='ease-in-expo',
    name='Ease In Expo',
    family='principles',
    group='Easing',
    aliases=('easeInExpo', 'exponential ease in', 'expo in'),
    definition='A move that barely creeps away from its start, then gathers speed sharply and is '
               'travelling at full tilt when it reaches the end.',
    phrasings=('starts really slowly then shoots off at the end',
               'lingers at first and then rockets away',
               'builds up speed dramatically before it leaves'),
    related=('slow-in-and-slow-out', 'smooth-scroll-inertia', 'friction-deceleration', 'interruptible-motion',
             'settle', 'asymmetric-fast-in-slow-out'),
    api=('videobuilder.ease_in_expo',),
    demo=lambda: demo.film(draw),
)
