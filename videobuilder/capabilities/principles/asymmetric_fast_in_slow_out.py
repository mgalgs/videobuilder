"""Asymmetric easing: an ease-in-out whose two halves differ, a short sharp
acceleration and a long gentle deceleration, so a thing leaves quickly and
takes its time arriving."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def asymmetric_ease(x, split=0.3):
    """Progress `x` in [0, 1] -> eased progress that speeds up over the first
    `split` of the time and slows down over the rest (`split` < 0.5 is fast
    in, slow out; 0.5 is a plain quadratic ease-in-out). Two parabolas meeting
    at peak speed, so position and velocity are both continuous."""
    x = vb.clamp01(x)
    if not 0 < split < 1:
        raise ValueError('split must be strictly between 0 and 1')
    if x < split:
        return x * x / split
    return 1 - (1 - x) ** 2 / (1 - split)


START, END = 0.4, 2.3     # the move, in seconds
TICK = 2                  # a spacing tick every this many frames


def _graph(cv, p):
    """Position over time, with the dot riding the curve up to `p`."""
    gx, gy, gw, gh = demo.W / 2 - 220, 40, 440, 250
    cv.line(gx, gy + gh, gx + gw, gy + gh, demo.LINE, width=2)
    cv.line(gx, gy, gx, gy + gh, demo.LINE, width=2)
    split = gx + gw * 0.3
    cv.line(split, gy, split, gy + gh, demo.MUTED, width=1, alpha=0.4)  # where speed peaks
    steps = 80
    pts = [(gx + gw * i / steps, gy + gh - gh * asymmetric_ease(i / steps)) for i in range(steps + 1)]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        cv.line(x0, y0, x1, y1, demo.MUTED, width=3, alpha=0.6)
    demo.dot(cv, gx + gw * p, gy + gh - gh * asymmetric_ease(p), r=10)
    f = demo.mono(18)
    vb.text.draw(cv, ['fast in'], f, gx + 12, gy + gh - 34, demo.MUTED)
    vb.text.draw(cv, ['slow out'], f, gx + gw - 96, gy + 36, demo.MUTED)


def draw(n, cv):
    p = demo.phase(n, START, END)
    _graph(cv, p)
    x0, x1, y = 120, demo.W - 120, 400
    cv.line(x0, y + 48, x1, y + 48, demo.LINE, width=2)
    first = round(START * demo.FPS)
    for k in range(first, min(n, round(END * demo.FPS)) + 1, TICK):  # the spacing so far
        tx = x0 + (x1 - x0) * asymmetric_ease(demo.phase(k, START, END))
        cv.line(tx, y + 36, tx, y + 60, demo.TEAL, width=2, alpha=0.9)
    cx = x0 + (x1 - x0) * asymmetric_ease(p)
    demo.dot(cv, cx, y, r=26)
    cv.mark('dot', cx - 26, y - 26, 52, 52)


TECHNIQUE = Technique(
    id='asymmetric-fast-in-slow-out',
    name='Asymmetric easing',
    family='principles',
    group='Timing & spacing',
    aliases=('fast in, slow out', 'asymmetric ease-in-out', 'quick start, long settle', 'standard easing'),
    definition='A move that gets up to speed in a short burst and then spends most of its time '
               'gliding gently to a stop.',
    phrasings=('takes off quickly and then drifts slowly into place',
               'snappy start with a long, soft landing',
               'ease in and out, but with much more of the ease at the end'),
    related=('linear-easing', 'eased-stagger', 'steps-easing', 'slow-in-and-slow-out', 'ease-in-out-quad',
             'ease-in-out-expo'),
    api=('videobuilder.techniques.principles.asymmetric_fast_in_slow_out.asymmetric_ease',),
    demo=lambda: demo.film(draw),
)
