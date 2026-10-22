"""Momentum Fling: a dragged thing is let go mid-swipe and keeps travelling at
the speed it was thrown, slowing smoothly under friction until it stops."""
import math

from .. import _demo as demo
from ..schema import Capability


def fling(t, velocity, decay=4.0):
    """Distance travelled `t` seconds after release when thrown at `velocity`
    (units per second, either sign): the speed falls off exponentially at rate
    `decay` per second, so it starts at `velocity` and glides to rest at
    `fling_rest(velocity, decay)`. Before release (t <= 0) it is 0."""
    if t <= 0:
        return 0.0
    return velocity / decay * (1 - math.exp(-decay * t))


def fling_rest(velocity, decay=4.0):
    """Where a fling thrown at `velocity` finally comes to rest, measured from
    the release point: velocity / decay."""
    return velocity / decay


def drag_and_fling(t, drag, drag_time, decay=4.0):
    """Offset of a drag-then-fling gesture at time `t` (seconds from touch-down):
    the finger pulls the object `drag` units in `drag_time` seconds, speeding up,
    and lets go; from there `fling` carries it on at the release speed
    (2 * drag / drag_time), so there is no jump in speed at the hand-off."""
    if t <= 0:
        return 0.0
    if t < drag_time:
        return drag * (t / drag_time) ** 2
    return drag + fling(t - drag_time, 2 * drag / drag_time, decay)


START, DRAG, DRAG_TIME, DOWN, DECAY = 170, 130, 0.4, 0.5, 1.6
CW, CH = 180, 112


def draw(n, cv):
    t = n / demo.FPS - DOWN
    y = demo.H / 2
    cv.line(80, y + CH / 2 + 34, demo.W - 80, y + CH / 2 + 34, demo.LINE, width=2)
    for i in range(16):  # a ruler under the track: the ticks make the slowing spacing readable
        tx = 80 + i * (demo.W - 160) / 15
        cv.line(tx, y + CH / 2 + 26, tx, y + CH / 2 + 42, demo.MUTED, width=2, alpha=0.6)
    for k in range(5, 0, -1):  # ghosts at earlier instants: wide gaps while fast, bunched as it stops
        x = START + drag_and_fling(t - k * 0.06, DRAG, DRAG_TIME, DECAY)
        cv.rect(x - CW / 2, y - CH / 2, CW, CH, demo.ACCENT, radius=14, alpha=0.07 * (6 - k))
    x = START + drag_and_fling(t, DRAG, DRAG_TIME, DECAY)
    demo.card(cv, x, y, w=CW, h=CH)
    # the finger: presses at the card's left part, drags with it, then lifts at release
    press = demo.phase(n, DOWN - 0.25, DOWN)
    lift = demo.phase(n, DOWN + DRAG_TIME, DOWN + DRAG_TIME + 0.3)
    fx = START - 40 + min(drag_and_fling(t, DRAG, DRAG_TIME, DECAY), DRAG) + 70 * lift
    fa = press * (1 - lift)
    if fa > 0:
        demo.dot(cv, fx, y + 10 - 30 * lift, 30, color=demo.INK, alpha=0.4 * fa)
        cv.arc(fx, y + 10 - 30 * lift, 30, 0, 2 * math.pi, demo.INK, width=4, alpha=fa)
    cv.mark('card', x - CW / 2, y - CH / 2, CW, CH)


CAPABILITY = Capability(
    id='momentum-fling',
    name='Momentum fling',
    family='ui',
    group='Gestures & drag',
    aliases=('fling', 'flick', 'throw', 'inertial drag', 'kinetic drag'),
    definition='Something dragged and let go mid-swipe keeps sliding at the speed it was thrown, '
               'then slows down smoothly until it comes to a stop.',
    phrasings=('flick the card and let it glide to a stop',
               'throw it across the screen and have it coast',
               'swipe it away so it keeps going on its own momentum'),
    related=('smooth-scroll-inertia', 'friction-deceleration', 'air-drag', 'bounce-ease-in', 'recoil',
             'scroll-velocity-skew'),
    api=('videobuilder.capabilities.ui.momentum_fling.drag_and_fling',
         'videobuilder.capabilities.ui.momentum_fling.fling',
         'videobuilder.capabilities.ui.momentum_fling.fling_rest'),
    demo=lambda: demo.film(draw),
)
