"""Settle: videobuilder already has it as an under-damped `vb.spring` (params
from `vb.damped`), so this entry only names it and demos it."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

START = 0.4
SPRING = vb.damped(0.18, hz=1.4)  # light damping: a few swings either side, each smaller than the last


def draw(n, cv):
    p = vb.spring(n / demo.FPS - START, **SPRING)
    x0, x1, y = demo.W / 2 - 300, demo.W / 2, demo.H / 2 - 80
    cv.line(x1, y - 100, x1, y + 260, demo.MUTED, width=2, alpha=0.5)  # where it comes to rest
    # the swings so far, traced underneath: a wave that dies down to the rest line
    pts = [(x0 + (x1 - x0) * vb.spring(k / demo.FPS - START, **SPRING), y + 105 + 1.6 * k) for k in range(n + 1)]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        cv.line(ax, ay, bx, by, demo.TEAL, width=3, alpha=0.6)
    demo.card(cv, x0 + (x1 - x0) * p, y)


CAPABILITY = Capability(
    id='settle',
    name='Settle',
    family='principles',
    group='Physics',
    aliases=('spring settle', 'damped oscillation', 'wobble to rest'),
    definition='After arriving, an object swings past its resting spot and back a few times, '
               'each swing smaller than the last, until it comes to a stop.',
    phrasings=('let it wobble a bit before it comes to rest',
               'springs into place and jiggles to a stop',
               'make it overshoot and rock back and forth before settling'),
    related=('bounce-ease-in', 'moving-hold', 'bounce-ease-out', 'ease-out-back', 'slow-in-and-slow-out',
             'ease-out-circ'),
    api=('videobuilder.spring', 'videobuilder.damped'),
    demo=lambda: demo.film(draw),
)
