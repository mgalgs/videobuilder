"""Slow In and Slow Out: the animation principle behind every ease-in-out
curve. videobuilder already has one as `vb.ease_in_out_quart`, so this entry
only names it and demos it, drawing the spacing chart: a mark wherever the
ball was every few frames, crowded at both ends and spread in the middle."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

START, END, EVERY = 0.4, 2.4, 3  # the move, in seconds; one spacing mark per EVERY frames


def draw(n, cv):
    r, y = 40, demo.H / 2 - 30
    x0, x1, track = 200, demo.W - 200, demo.H / 2 + 60
    at = lambda f: x0 + (x1 - x0) * vb.ease_in_out_quart(demo.phase(f, START, END))  # noqa: E731
    demo.floor(cv, track, color=demo.LINE)
    for f in range(round(START * demo.FPS), min(n, round(END * demo.FPS)) + 1, EVERY):
        x = at(f)
        demo.dot(cv, x, y, r, alpha=0.08)                        # onion skin of where it was
        cv.line(x, track - 12, x, track + 12, demo.TEAL, width=3)  # and its tick on the spacing chart
    x = at(n)
    cv.line(x, y + r + 8, x, track - 14, demo.MUTED, width=2, alpha=0.6)
    demo.dot(cv, x, y, r)
    cv.mark('ball', x - r, y - r, 2 * r, 2 * r)


CAPABILITY = Capability(
    id='slow-in-and-slow-out',
    name='Slow In and Slow Out',
    family='principles',
    group='Disney principles',
    aliases=('slow-in slow-out', 'ease in ease out principle', 'spacing principle'),
    definition='A move that gathers speed gently from rest and gently sheds it again before stopping, '
               'so most of its frames sit near the two ends and few in the fast middle.',
    phrasings=('let it start slow, speed up, then slow down before it stops',
               'ease it in and out so it does not jerk at either end',
               'make the move feel natural instead of robotic'),
    related=('ease-in-out-expo', 'ease-out-sine', 'ease-out-expo', 'asymmetric-fast-in-slow-out',
             'ease-in-out-quint', 'ease-in-out-back'),
    api=('videobuilder.ease_in_out_quart', 'videobuilder.bezier'),
    demo=lambda: demo.film(draw),
)
