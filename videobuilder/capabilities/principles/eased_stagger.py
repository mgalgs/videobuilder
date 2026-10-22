"""Eased Stagger: a stagger whose start times are spaced along an easing curve
instead of evenly, so the first items go off close together and the gaps
widen towards the last (or the other way round, with another curve)."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def ease_in_quad(x):
    """The default spacing curve: gentle at first, so early starts bunch up."""
    return x * x


def stagger_starts(count, span=1.0, ease=ease_in_quad):
    """The start times of `count` items spread over `span`: item `i` starts at
    `span * ease(i / (count - 1))`. A linear `ease` gives an even stagger; an
    ease-in bunches the first starts, an ease-out bunches the last."""
    if count <= 1:
        return [0.0] * count
    return [span * ease(i / (count - 1)) for i in range(count)]


def eased_stagger(p, i, count, ease=ease_in_quad, each=0.3, item_ease=vb.ease_out_expo):
    """Item `i` of `count`'s own progress (0 -> 1) at overall progress `p`.
    Each item animates for `each` of the whole; their starts are spaced by
    `ease` (see `stagger_starts`) so the last one finishes exactly at 1.
    `item_ease` shapes each item's own move."""
    start = stagger_starts(count, 1 - each, ease)[i]
    return item_ease(vb.clamp01((p - start) / each))


N = 12


def draw(n, cv):
    p = demo.phase(n, 0.3, 2.6)
    bw, bh, gap = 34, 150, 30
    x0 = (demo.W - (N * bw + (N - 1) * gap)) / 2
    y = demo.H / 2 - bh / 2 - 60
    for i in range(N):
        x = x0 + i * (bw + gap)
        cv.outline(x, y, bw, bh, demo.LINE, width=2, radius=bw / 2, alpha=0.6)  # each bar's resting slot
        q = eased_stagger(p, i, N, each=0.22)
        if q > 0:
            cv.rect(x, y + 70 * (1 - q), bw, bh, demo.ACCENT, radius=bw / 2, alpha=q)
    # a timeline under the row: one tick per start time, so the widening gaps are visible
    ty, tx0, tx1 = y + bh + 120, x0, x0 + N * bw + (N - 1) * gap
    cv.line(tx0, ty, tx1, ty, demo.MUTED, width=2, alpha=0.6)
    for s in stagger_starts(N, 1 - 0.22):
        tx = tx0 + (tx1 - tx0) * s
        cv.line(tx, ty - 14, tx, ty + 14, demo.ACCENT if p >= s else demo.MUTED, width=3)
    hx = tx0 + (tx1 - tx0) * p
    demo.dot(cv, hx, ty, 9, color=demo.INK)
    cv.mark('row', x0, y, tx1 - tx0, bh)


CAPABILITY = Capability(
    id='eased-stagger',
    name='Eased Stagger',
    family='principles',
    group='Stagger',
    aliases=('stagger with easing', 'ease distribution stagger'),
    definition='Items in a sequence start one after another with the gaps between their start times '
               'following an easing curve, so they rush in close together and then trail out slower.',
    phrasings=('stagger these but have them speed up or slow down as they go',
               'the first few come in quickly, then the rest arrive further apart',
               'cascade the bars in with the delays easing out instead of even spacing'),
    related=('asymmetric-fast-in-slow-out', 'linear-easing', 'linear-repeater-stagger', 'per-word-fade-in',
             'steps-easing', 'ease-out-expo'),
    api=('videobuilder.capabilities.principles.eased_stagger.eased_stagger',
         'videobuilder.capabilities.principles.eased_stagger.stagger_starts'),
    demo=lambda: demo.film(draw),
)
