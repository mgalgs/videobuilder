"""Delay: a move that waits a set time before it starts, holding still at its
start until then and running its full length after."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def delayed(t, delay, duration, ease=vb.ease_in_out_quart):
    """Eased progress 0 -> 1 at time `t` of a move that starts `delay` after
    0 and lasts `duration` (any one unit: seconds or frames). It reads 0 for
    the whole wait and 1 once the move is done. `ease` shapes the move itself."""
    return ease(vb.clamp01((t - delay) / duration))


START, MOVE, DELAY = 0.35, 1.2, 0.9


def lane(cv, y, label, p, waiting, color):
    x0, x1 = 300, demo.W - 200
    demo.floor(cv, y + 40, color=demo.LINE)
    demo.word(cv, label, 150, y, size=30, color=demo.MUTED, weight=700)
    x = x0 + (x1 - x0) * p
    if waiting is not None:  # a ring sweeping round the held dot while the delay runs out
        cv.arc(x, y, 52, -math.pi / 2, -math.pi / 2 + 2 * math.pi * waiting, demo.INK, width=5, alpha=0.8)
    demo.dot(cv, x, y, color=color)
    cv.mark(label, x - 34, y - 34, 68, 68)


def draw(n, cv):
    t = n / demo.FPS
    top, bottom = demo.H / 2 - 120, demo.H / 2 + 120
    lane(cv, top, 'no delay', delayed(t - START, 0, MOVE), None, demo.MUTED)
    wait = (t - START) / DELAY
    lane(cv, bottom, f'delay {DELAY:g} s', delayed(t - START, DELAY, MOVE),
         wait if 0 < wait < 1 else None, demo.ACCENT)


CAPABILITY = Capability(
    id='delay',
    name='Delay',
    family='principles',
    group='Principle sub-capabilities',
    aliases=('start delay', 'animation-delay', 'pre-roll'),
    definition='An element holds still for a set moment and only then begins its move, '
               'so the action starts later than its cue.',
    phrasings=('wait a beat before it starts moving',
               'have it sit there for a second and then slide across',
               'start the animation a little later than the others'),
    related=('interruptible-motion', 'frame-delay-echo', 'linear-stagger', 'timing', 'overlapping-action',
             'seamless-loop'),
    api=('videobuilder.capabilities.principles.delay.delayed',),
    demo=lambda: demo.film(draw),
)
