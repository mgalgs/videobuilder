"""Ease In Cubic: an easing curve that sets off almost imperceptibly and then
speeds up harder and harder, arriving at full speed -- progress cubed."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def ease_in_cubic(x):
    """Progress `x` in [0, 1] -> eased progress `x**3`: slow away from 0,
    steepest (three times linear speed) as it reaches 1."""
    x = vb.clamp01(x)
    return x * x * x


START, END = 0.5, 2.3  # seconds the move runs
STEPS = 12  # time-spaced marks: their widening gaps show the speed building


def draw(n, cv):
    t = demo.phase(n, START, END)
    x0, x1, y = 120, demo.W - 120, 150
    track = lambda p: x0 + (x1 - x0) * p  # noqa: E731
    cv.line(x0, y + 52, x1, y + 52, demo.LINE, width=3)
    cv.line(x0, y + 52, track(ease_in_cubic(t)), y + 52, demo.TEAL, width=4)
    for i in range(1, STEPS):  # where the dot was at equal steps of time, once it has passed them
        s = i / STEPS
        if s <= t:
            demo.dot(cv, track(ease_in_cubic(s)), y, 20, color=demo.MUTED, alpha=0.22)
    demo.dot(cv, track(ease_in_cubic(t)), y, 28)
    cv.mark('dot', track(ease_in_cubic(t)) - 28, y - 28, 56, 56)

    gx, gy, gw, gh = demo.W / 2 - 170, 260, 340, 200  # the curve itself, traced as it plays
    cv.line(gx, gy + gh, gx + gw, gy + gh, demo.LINE, width=2)
    cv.line(gx, gy, gx, gy + gh, demo.LINE, width=2)
    seg = 60
    for i in range(seg):
        a, b = i / seg, (i + 1) / seg
        done = b <= t
        cv.line(gx + gw * a, gy + gh * (1 - ease_in_cubic(a)), gx + gw * b, gy + gh * (1 - ease_in_cubic(b)),
                demo.TEAL if done else demo.MUTED, width=3 if done else 2, alpha=1.0 if done else 0.35)
    demo.dot(cv, gx + gw * t, gy + gh * (1 - ease_in_cubic(t)), 7, color=demo.INK)


CAPABILITY = Capability(
    id='ease-in-cubic',
    name='Ease In Cubic',
    family='principles',
    group='Easing',
    aliases=('easeInCubic', 'power3 in', 'cubic in'),
    definition='A move that creeps away from its start and keeps accelerating, '
               'so it is going fastest at the moment it arrives.',
    phrasings=('starts slow and speeds up as it goes',
               'builds up speed and shoots off at the end',
               'accelerates out, like it is gathering momentum'),
    related=('slow-in-and-slow-out', 'smooth-scroll-inertia', 'asymmetric-fast-in-slow-out',
             'friction-deceleration', 'three-d-word-cube', 'push-in'),
    api=('videobuilder.capabilities.principles.ease_in_cubic.ease_in_cubic',),
    demo=lambda: demo.film(draw),
)
