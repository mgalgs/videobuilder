"""Friction Deceleration: a thing let go at speed loses the same share of its
speed every instant, so it slows hard at first and then coasts ever more
gently to a stop -- exponential decay of velocity, as an easing curve and as
a physical slide from a starting velocity."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def friction_ease(x, friction=5.0):
    """Progress `x` in [0, 1] -> eased progress under constant friction:
    velocity decays as e^(-friction * x), normalised so the curve lands on 1
    at x = 1. Higher `friction` front-loads the move and lengthens the coast."""
    x = vb.clamp01(x)
    if friction <= 0:
        return x
    return (1 - math.exp(-friction * x)) / (1 - math.exp(-friction))


def friction_slide(t, velocity, friction=4.0):
    """Distance covered `t` seconds after release at `velocity` (units/s) when
    friction removes `friction` per second of the current speed. Comes to rest
    at velocity / friction; call it per frame for a fling that coasts out."""
    if t <= 0:
        return 0.0
    return velocity / friction * (1 - math.exp(-friction * t))


START, END, FRICTION = 0.3, 2.6, 5.0
STEP = 3  # a tick is dropped where the ball was every this many frames


def _x(n):
    x0, x1 = 220, demo.W - 220
    return x0 + (x1 - x0) * friction_ease(demo.phase(n, START, END), FRICTION)


def draw(n, cv):
    r, ground = 48, demo.H / 2 + 60
    y = ground - r
    x0 = _x(0)
    demo.floor(cv, ground)
    cv.outline(x0 - r, y - r, 2 * r, 2 * r, demo.MUTED, width=2, radius=r, alpha=0.5)  # where it was let go
    # Ticks at the ball's past positions: the gaps shrink as friction bleeds the speed off.
    last = None
    for k in range(round(START * demo.FPS), n + 1, STEP):
        tx = _x(k)
        if last is None or tx - last >= 5:  # once it has all but stopped, ticks would only pile up
            cv.line(tx, ground + 14, tx, ground + 40, demo.MUTED, width=2, alpha=0.8)
            last = tx
    x = _x(n)
    p = demo.phase(n, START, END)
    speed = math.exp(-FRICTION * p) if 0 < p < 1 else 0.0  # 1 at release, fading to 0
    if speed > 0.01:  # a velocity arrow above the ball, shrinking with its speed
        ay, length = y - r - 50, 260 * speed
        cv.line(x - length / 2, ay, x + length / 2, ay, demo.TEAL, width=4)
        cv.line(x + length / 2, ay, x + length / 2 - 16, ay - 10, demo.TEAL, width=4)
        cv.line(x + length / 2, ay, x + length / 2 - 16, ay + 10, demo.TEAL, width=4)
    demo.dot(cv, x, y, r)
    cv.mark('ball', x - r, y - r, 2 * r, 2 * r)


CAPABILITY = Capability(
    id='friction-deceleration',
    name='Friction Deceleration',
    family='principles',
    group='Physics',
    aliases=('exponential decay', 'friction slide', 'decay easing', 'fling', 'flick', 'inertial drag'),
    definition='Something released at speed sheds a constant share of that speed each moment, '
               'so it brakes sharply at first and then drifts slower and slower into a soft stop.',
    phrasings=('let it glide and slow down on its own like it is sliding on ice',
               'push it and have it coast to a stop',
               'starts quick and gradually loses steam until it rests'),
    related=('linear-easing', 'momentum-fling', 'smooth-scroll-inertia', 'slow-in-and-slow-out',
             'slow-motion', 'ease-out-expo'),
    api=('videobuilder.capabilities.principles.friction_deceleration.friction_ease',
         'videobuilder.capabilities.principles.friction_deceleration.friction_slide'),
    demo=lambda: demo.film(draw),
)
