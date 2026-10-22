"""Newton's Cradle: a row of touching balls hung side by side; the end ball
swings in and stops dead on the row, and the ball at the far end flies out,
swings back and knocks the first one out again, the middle ones never moving."""
import math

from .. import _demo as demo
from ..principles.pendulum_swing import pendulum_point
from ..schema import Technique


def cradle_angles(t, count=5, lifted=1, amplitude=0.55, period=1.4, decay=0.0):
    """Angle in radians from straight down of each of `count` hanging balls,
    left to right, at `t` seconds (positive swings right). At `t` = 0 the
    `lifted` leftmost balls are pulled out by `amplitude` and let go; they hit
    the row a quarter `period` later and stop, and the `lifted` rightmost balls
    swing out instead, and so on, one full exchange per `period`. `decay` > 0
    shrinks the swing by e^(-decay * t). Before 0 the lifted balls hang held out.

    Closed form, so any frame evaluates alone. Place each ball with
    `pendulum_point` from its own pivot, the pivots one ball-width apart."""
    lifted = max(1, min(lifted, count - 1))
    t = max(t, 0.0)
    swing = -amplitude * math.exp(-decay * t) * math.cos(2 * math.pi * t / period)
    angles = [0.0] * count
    if swing < 0:  # the left group is out; the rest hang in contact
        angles[:lifted] = [swing] * lifted
    else:
        angles[count - lifted:] = [swing] * lifted
    return angles


COUNT, R = 5, 52
PIVOT_Y, ARM, AMP, PERIOD, RELEASE = demo.H * 0.2, demo.H * 0.5, 0.62, 1.3, 0.3
X0 = demo.W / 2 - (COUNT - 1) * R


def draw(n, cv):
    t = n / demo.FPS - RELEASE
    top = PIVOT_Y - 6
    cv.rect(X0 - R - 160, top - 14, (COUNT - 1) * 2 * R + 2 * R + 320, 14, demo.MUTED, radius=7)  # the frame
    demo.floor(cv, PIVOT_Y + ARM + R + 40, color=demo.LINE)
    for k in (3, 2, 1):  # ghosts a few frames back, so the moving end balls read as swinging
        for i, a in enumerate(cradle_angles(t - 0.035 * k, COUNT, 1, AMP, PERIOD)):
            if a:
                x, y = pendulum_point(X0 + 2 * R * i, PIVOT_Y, ARM, a)
                demo.dot(cv, x, y, R, alpha=0.2 - 0.05 * k)
    for i, a in enumerate(cradle_angles(t, COUNT, 1, AMP, PERIOD)):
        px = X0 + 2 * R * i
        x, y = pendulum_point(px, PIVOT_Y, ARM, a)
        for side in (-1, 1):  # two strings per ball, in a V, as on the desk toy
            cv.line(px + side * R * 0.7, top, x, y, demo.INK, width=2, alpha=0.7)
        demo.dot(cv, x, y, R, color=demo.ACCENT if i in (0, COUNT - 1) else demo.INK)
        demo.dot(cv, x - R * 0.35, y - R * 0.35, R * 0.22, color='#ffffff', alpha=0.35)  # a glint
        cv.mark(f'ball{i}', x - R, y - R, 2 * R, 2 * R)


TECHNIQUE = Technique(
    id='newton-s-cradle',
    name="Newton's cradle",
    family='particles',
    group='Rigid bodies',
    aliases=('Newton\'s balls', 'executive ball clicker', 'momentum balls', 'balance balls',
             'collision pendulums'),
    definition='Balls hanging in a touching row pass a swing along the line: one end ball drops in and stops '
               'dead, the far end ball leaps out and back, and the ones between stay still.',
    phrasings=('the desk toy where the balls click back and forth',
               'one ball hits the row and the one on the other end swings out',
               'pass the momentum down a line of hanging balls'),
    related=('elastic-collisions', 'momentum-fling', 'ball-bounce', 'magnetic-snap', 'offset', 'recoil'),
    api=('videobuilder.techniques.particles.newton_s_cradle.cradle_angles',
         'videobuilder.techniques.principles.pendulum_swing.pendulum_point'),
    demo=lambda: demo.film(draw),
)
