"""Ease In-Out Back: an easing curve that winds up by backing away from the
target before it sets off, then runs past the target and settles back onto
it -- an overshoot at both ends of the move."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def ease_in_out_back(x, overshoot=1.70158):
    """Progress `x` in [0, 1] -> eased progress that dips below 0 early and
    rises above 1 late. `overshoot` sets how far: the default backs off and
    overshoots by about 10% of the move; 0 is a plain cubic ease in-out."""
    x = vb.clamp01(x)
    s = overshoot * 1.525  # rescaled so each half's dip matches a single-ended back ease
    if x < 0.5:
        u = 2 * x
        return u * u * ((s + 1) * u - s) / 2
    u = 2 * x - 2
    return (u * u * ((s + 1) * u + s) + 2) / 2


def draw(n, cv):
    t = demo.phase(n, 0.5, 2.3)
    p = ease_in_out_back(t)
    x0, x1, y = demo.W / 2 - 250, demo.W / 2 + 250, demo.H / 2 - 70
    for x in (x0, x1):  # where it starts and where it comes to rest
        cv.outline(x - 91, y - 56, 182, 112, demo.MUTED, width=2, radius=13, alpha=0.5)
    demo.card(cv, x0 + (x1 - x0) * p, y, scale=0.7)

    # The curve itself, small, under the card: a dot rides it as the card moves.
    gw, gh = 260, 100
    gx, gy = demo.W / 2 - gw / 2, demo.H - 70
    cv.line(gx, gy, gx + gw, gy, demo.LINE, width=2, alpha=0.6)
    cv.line(gx, gy - gh, gx + gw, gy - gh, demo.LINE, width=2, alpha=0.6)
    steps = 60
    pts = [(gx + gw * i / steps, gy - gh * ease_in_out_back(i / steps)) for i in range(steps + 1)]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        cv.line(ax, ay, bx, by, demo.MUTED, width=3)
    demo.dot(cv, gx + gw * t, gy - gh * p, 8)


TECHNIQUE = Technique(
    id='ease-in-out-back',
    name='Ease In-Out Back',
    family='principles',
    group='Easing',
    aliases=('back in-out', 'ease in out back', 'anticipate and overshoot'),
    definition='A move that first pulls back a little away from where it is going, swings across, '
               'shoots slightly past the target and then settles back onto it.',
    phrasings=('winds up backwards, then slides over and overshoots before settling',
               'pulls back before it goes and overshoots when it lands',
               'a slide with a little wind-up at the start and a bounce-back at the end'),
    related=('dolly-in-and-out', 'slow-in-and-slow-out', 'reverse-playback', 'follow-through',
             'overshoot-bounce-in', 'interruptible-motion'),
    api=('videobuilder.techniques.principles.ease_in_out_back.ease_in_out_back',),
    demo=lambda: demo.film(draw),
)
