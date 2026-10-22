"""Ease In-Out Expo: an exponential S-curve that barely moves at either end
and covers almost all the distance in a quick burst through the middle, so
a move reads as a snap from one state to the next."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def ease_in_out_expo(x):
    """Progress `x` in [0, 1] -> eased progress: 2^(20x-10)/2 on the way in,
    its mirror on the way out, so the first and last fifths move only a few
    percent and the middle does the rest."""
    x = vb.clamp01(x)
    if x in (0.0, 1.0):
        return x
    if x < 0.5:
        return 2 ** (20 * x - 10) / 2
    return (2 - 2 ** (-20 * x + 10)) / 2


START, END = 0.4, 2.4  # seconds the move runs
STEPS = 16             # spacing ticks: where the dot is at even slices of time


def draw(n, cv):
    t = demo.phase(n, START, END)
    p = ease_in_out_expo(t)
    x0, x1, ty = 180, demo.W - 180, demo.H / 2 - 80

    # The track, with a tick at every even slice of time: they bunch at the
    # ends and spread wide in the middle, which is the curve's whole shape.
    demo.floor(cv, ty, color=demo.LINE)
    for i in range(STEPS + 1):
        x = x0 + (x1 - x0) * ease_in_out_expo(i / STEPS)
        cv.line(x, ty - 9, x, ty + 9, demo.MUTED, width=2, alpha=0.7)
    cv.line(x0, ty, x0 + (x1 - x0) * p, ty, demo.TEAL, width=4)

    # The curve itself, traced up to now, with a marker riding it.
    gx, gy, gw, gh = x0, demo.H / 2 + 20, x1 - x0, 190
    cv.line(gx, gy + gh, gx + gw, gy + gh, demo.LINE, width=2)
    cv.line(gx, gy, gx, gy + gh, demo.LINE, width=2)
    pts = [(gx + gw * i / 120, gy + gh * (1 - ease_in_out_expo(i / 120))) for i in range(121)]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        cv.line(ax, ay, bx, by, demo.MUTED, width=2, alpha=0.4)
    now = (gx + gw * t, gy + gh * (1 - p))
    done = [pt for pt in pts if pt[0] < now[0]] + [now]
    for (ax, ay), (bx, by) in zip(done, done[1:]):
        cv.line(ax, ay, bx, by, demo.TEAL, width=4)
    demo.dot(cv, *now, 7, color=demo.INK)

    demo.dot(cv, x0 + (x1 - x0) * p, ty - 60, 36)
    cv.mark('dot', x0 + (x1 - x0) * p - 36, ty - 96, 72, 72)


TECHNIQUE = Technique(
    id='ease-in-out-expo',
    name='Ease In-Out Expo',
    family='principles',
    group='Easing',
    aliases=('easeInOutExpo', 'exponential in-out', 'expo in-out'),
    definition='A move that creeps off its start, whips through the middle almost at once, '
               'then creeps into its end, so it feels like a snap between two resting states.',
    phrasings=('hangs still, then snaps across and settles slowly',
               'a really sharp ease in and out, slow at both ends and very fast in between',
               'make it whoosh across the middle but linger at the start and end'),
    related=('slow-in-and-slow-out', 'smooth-scroll-inertia', 'asymmetric-fast-in-slow-out',
             'dolly-in-and-out', 'push-in', 'empty-state-idle-loop'),
    api=('videobuilder.techniques.principles.ease_in_out_expo.ease_in_out_expo',),
    demo=lambda: demo.film(draw),
)
