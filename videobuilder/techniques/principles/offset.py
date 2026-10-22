"""Offset: linked parts run the very same move, but each one sets off a beat
after the one before, so the group reads as separate weights dragging along
rather than one rigid block."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def offset(p, i, count, lag=0.15, ease=vb.ease_in_out_quart):
    """Eased progress of part `i` of `count` at overall progress `p` (0 -> 1).
    Every part runs the same move over the same length; part 0 starts at 0,
    each later part `lag` (a fraction of the whole) after the one before, and
    the last finishes at 1. `ease` shapes each part's own move."""
    if count < 2:
        return ease(vb.clamp01(p))
    lag = min(max(lag, 0.0), 1.0 / (count - 1))
    span = 1 - lag * (count - 1)
    if span <= 0:
        return 1.0 if p >= i * lag else 0.0
    return ease(vb.clamp01((p - i * lag) / span))


def draw(n, cv):
    p = demo.phase(n, 0.4, 2.6)
    x0, x1 = 320, demo.W - 320
    ys = (demo.H / 2 - 170, demo.H / 2, demo.H / 2 + 170)
    pts = [(x0 + (x1 - x0) * offset(p, i, len(ys), lag=0.2), y) for i, y in enumerate(ys)]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):  # the links, so the parts read as one chain
        cv.line(ax, ay, bx, by, demo.MUTED, width=4)
    for i, (x, y) in enumerate(pts):
        demo.dot(cv, x, y, 40, color=demo.ACCENT if i == 0 else demo.TEAL)
        cv.mark(f'part{i}', x - 40, y - 40, 80, 80)


TECHNIQUE = Technique(
    id='offset',
    name='Offset',
    family='principles',
    group='Principle sub-techniques',
    aliases=('timing offset', 'staggered start'),
    definition='Connected parts make the same move but start it one after another, a beat apart, '
               'so each seems to carry its own weight and trail the one ahead.',
    phrasings=('have the pieces follow each other a moment late instead of moving together',
               'start the same motion a little later for each part so it feels like it drags',
               'make the chain move with the first part leading and the rest catching up'),
    related=('overlapping-action', 'random-stagger', 'offset-path-expansion', 'timing', 'proximity-stagger',
             'linear-stagger'),
    api=('videobuilder.techniques.principles.offset.offset',),
    demo=lambda: demo.film(draw),
)
