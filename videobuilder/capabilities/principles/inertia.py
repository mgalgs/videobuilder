"""Inertia: something with mass chasing an input that jumps. It can't match
the jump at once -- it gathers speed, and when the input turns back it keeps
going the old way a moment before the pull wins and it reverses."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def inertia(t, moves, start=0.0, ratio=1.0, hz=0.9):
    """Where a weighty object is at `t` seconds when it follows an input that
    starts at `start` and jumps to `value` at each `(time, value)` in `moves`.

    The object is a damped spring on the input (`vb.damped(ratio, hz)`); the
    system is linear, so the answer is the sum of one `vb.spring` step
    response per jump -- closed form, any frame evaluates alone. Lower `hz`
    is heavier (more lag); `ratio` 1 settles without overshoot, below 1 sails
    past the target and swings back."""
    params = vb.damped(ratio, hz)
    x, prev = start, start
    for at, value in moves:
        x += (value - prev) * vb.spring(t - at, **params)
        prev = value
    return x


def inertia_velocity(t, moves, start=0.0, ratio=1.0, hz=0.9, dt=1e-3):
    """The object's velocity (units per second) at `t`, for `inertia` with the same arguments."""
    return (inertia(t + dt, moves, start, ratio, hz) - inertia(t - dt, moves, start, ratio, hz)) / (2 * dt)


LEFT, RIGHT = demo.W / 2 - 300, demo.W / 2 + 300
# the handle turns back while the object is mid-rail and at full speed, so the
# coast past that moment is long and is still going at the poster frame (2.1 s)
MOVES = ((0.3, RIGHT), (1.75, LEFT))
TURN = MOVES[1][0]
HEAVY = dict(ratio=0.3, hz=0.18)  # heavy and loosely damped: slow to start, slow to stop
RAIL, LANE = 130, 320


def _input_at(t):
    x = LEFT
    for at, value in MOVES:
        if t >= at:
            x = value
    return x


def _label(cv, text, x, y, color=demo.MUTED):
    vb.text.draw(cv, [text], demo.mono(16), x, y, color)


def draw(n, cv):
    t = n / demo.FPS
    target = _input_at(t)
    x = inertia(t, MOVES, start=LEFT, **HEAVY)
    v = inertia_velocity(t, MOVES, start=LEFT, **HEAVY)
    # the input: a handle that snaps between the ends of its rail
    cv.line(LEFT - 40, RAIL, RIGHT + 40, RAIL, demo.LINE, width=3)
    cv.line(target, RAIL, target, LANE + 52, demo.TEAL, width=2, alpha=0.55)
    demo.dot(cv, target, RAIL, 13, color=demo.TEAL)
    demo.dot(cv, target, RAIL, 5, color=demo.BG)
    _label(cv, 'input', LEFT - 40, RAIL - 40)
    # the object: lags the handle, and coasts on when the handle turns back
    cv.line(LEFT - 40, LANE + 52, RIGHT + 40, LANE + 52, demo.LINE, width=3)
    if t >= TURN:
        # where the object was when the handle turned back: it coasts on past this
        turned = inertia(TURN, MOVES, start=LEFT, **HEAVY)
        cv.line(turned, LANE - 70, turned, LANE + 52, demo.MUTED, width=2, alpha=0.6)
        _label(cv, 'handle turned', turned - 60, LANE - 96)
    demo.dot(cv, x, LANE, 46)
    cv.mark('object', x - 46, LANE - 46, 92, 92)
    _label(cv, 'object', LEFT - 40, LANE - 96)
    # its velocity, as an arrow under it
    length = v * 0.3
    if abs(length) > 4:
        y, tip = LANE + 90, x + length
        head = 13 if length > 0 else -13
        cv.line(x, y, tip, y, demo.INK, width=4)
        cv.line(tip, y, tip - head, y - 9, demo.INK, width=4)
        cv.line(tip, y, tip - head, y + 9, demo.INK, width=4)


CAPABILITY = Capability(
    id='inertia',
    name='Inertia',
    family='principles',
    group='Physics',
    aliases=('inertial motion', 'resistance to change'),
    definition='A heavy object trails behind whatever drives it, building up speed slowly and carrying on '
               'in the same direction for a moment after the drive turns around.',
    phrasings=('make it feel heavy, like it lags behind and takes a moment to stop',
               'it should keep drifting the old way before it turns back',
               'give it some weight so it catches up instead of snapping'),
    related=('linear-easing', 'slow-in-and-slow-out', 'momentum-fling', 'velocity-preserving-retarget',
             'bounce-ease-in', 'ease-in-out-back'),
    api=('videobuilder.capabilities.principles.inertia.inertia',
         'videobuilder.capabilities.principles.inertia.inertia_velocity',
         'videobuilder.spring', 'videobuilder.damped'),
    demo=lambda: demo.film(draw),
)
