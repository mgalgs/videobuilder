"""Edge-In Stagger: a row of items enters from its two ends at once, pair by
pair, so the arrivals close in on the middle and the centre item lands last."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def edge_in_rank(i, count):
    """Item `i` of `count` -> its turn in an edge-in stagger: 0 for both end
    items, 1 for the pair inside them, and so on up to the centre."""
    return min(i, count - 1 - i)


def edge_in_stagger(i, count, p, spread=0.6):
    """Item `i`'s own progress (0 -> 1) at group progress `p` (0 -> 1).
    Mirrored items share a start; the end pair starts at 0 and the innermost
    item at `spread`, each taking the remaining `1 - spread` to finish, so
    every item is done when `p` reaches 1. Ease the result as you like."""
    last = (count - 1) // 2
    start = spread * edge_in_rank(i, count) / last if last else 0.0
    return vb.clamp01((vb.clamp01(p) - start) / (1 - spread))


def draw(n, cv):
    count, w, h, gap = 11, 62, 84, 14
    x0 = (demo.W - (count * w + (count - 1) * gap)) / 2
    y = demo.H / 2 - h / 2
    p = demo.phase(n, 0.3, 2.3)
    for i in range(count):
        x = x0 + i * (w + gap)
        cv.outline(x, y, w, h, demo.MUTED, width=2, radius=12, alpha=0.35)  # the empty slot
        q = edge_in_stagger(i, count, p, spread=0.7)
        if q <= 0:
            continue
        rise = 1 - vb.ease_out_back(q)
        with cv.layer(opacity=min(1.0, q * 3)):
            cv.rect(x, y + 90 * rise, w, h, demo.ACCENT, radius=12)
        cv.mark(f'item{i}', x, y + 90 * rise, w, h)


CAPABILITY = Capability(
    id='edge-in-stagger',
    name='Edge-In Stagger',
    family='principles',
    group='Stagger',
    aliases=('outside-in stagger', 'from-edges stagger', 'stagger from edges'),
    definition='The two outermost items of a row arrive first, then each next pair inward, '
               'so the entrances close in on the middle and the centre lands last.',
    phrasings=('bring the items in from both ends toward the centre',
               'stagger them outside-in so they meet in the middle',
               'have the row fill in from the edges inward'),
    related=('staggered-cascade-reveal', 'character-scale-in', 'linear-repeater-stagger', 'seamless-loop',
             'per-word-fade-in', 'offset'),
    api=('videobuilder.capabilities.principles.edge_in_stagger.edge_in_stagger',
         'videobuilder.capabilities.principles.edge_in_stagger.edge_in_rank'),
    demo=lambda: demo.film(draw),
)
