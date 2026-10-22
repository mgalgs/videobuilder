"""Pendulum Swing: a weight on a rigid arm rocks to and fro about a fixed pivot,
pausing at each end of its arc and moving fastest as it passes the bottom."""
import math

from .. import _demo as demo
from ..schema import Capability


def pendulum_angle(t, amplitude=0.6, period=1.5, decay=0.0, phase=0.0):
    """Angle in radians of the arm from straight down at `t` seconds: starts
    out at `amplitude` (positive swings right), back again after `period`
    seconds. `decay` > 0 shrinks the swing by e^(-decay * t), so it winds
    down to rest; `phase` (in cycles) shifts where in the swing `t = 0` falls.

    Closed form, so any frame evaluates alone. Rotate a layer about the pivot
    by it, or place the weight with `pendulum_point`."""
    return amplitude * math.exp(-decay * max(t, 0.0)) * math.cos(2 * math.pi * (t / period + phase))


def pendulum_point(px, py, length, angle):
    """Where the end of an arm of `length` hanging from (px, py) sits at `angle`."""
    return px + length * math.sin(angle), py + length * math.cos(angle)


PIVOT_X, PIVOT_Y, ARM, AMP, PERIOD, BOB = demo.W / 2, demo.H * 0.14, demo.H * 0.62, 0.62, 1.5, demo.H * 0.06


def draw(n, cv):
    t = n / demo.FPS
    cv.arc(PIVOT_X, PIVOT_Y, ARM, math.pi / 2 - AMP, math.pi / 2 + AMP, demo.LINE, width=3)  # the path it sweeps
    cv.line(PIVOT_X - 50, PIVOT_Y, PIVOT_X + 50, PIVOT_Y, demo.MUTED, width=4)
    for k in (3, 2, 1):  # ghosts a few frames back: spread wide where it's fast, bunched where it turns
        x, y = pendulum_point(PIVOT_X, PIVOT_Y, ARM, pendulum_angle(t - 0.04 * k, AMP, PERIOD))
        demo.dot(cv, x, y, BOB, alpha=0.22 - 0.05 * k)
    x, y = pendulum_point(PIVOT_X, PIVOT_Y, ARM, pendulum_angle(t, AMP, PERIOD))
    cv.line(PIVOT_X, PIVOT_Y, x, y, demo.INK, width=5)
    demo.dot(cv, PIVOT_X, PIVOT_Y, 8, color=demo.INK)
    demo.dot(cv, x, y, BOB)
    cv.mark('bob', x - BOB, y - BOB, 2 * BOB, 2 * BOB)


CAPABILITY = Capability(
    id='pendulum-swing',
    name='Pendulum Swing',
    family='principles',
    group='Physics',
    aliases=('pendulum motion', 'simple harmonic pendulum', 'swinging shape', 'hanging weight swing'),
    definition='A weight on a stiff arm rocks side to side about a fixed point above it, '
               'hanging still for an instant at each end and rushing fastest through the bottom.',
    phrasings=('swings back and forth like a clock pendulum',
               'hangs from a pin and rocks side to side',
               'make the sign sway on its hook'),
    related=('bezier-handle-bend', 'door-swing', 'slant-axis-swing', 'walk-cycle', 'newton-s-cradle',
             'ping-pong-loop'),
    api=('videobuilder.capabilities.principles.pendulum_swing.pendulum_angle',
         'videobuilder.capabilities.principles.pendulum_swing.pendulum_point'),
    demo=lambda: demo.film(draw),
)
