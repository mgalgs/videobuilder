"""Layout animation (FLIP): when a layout changes, each item glides and
resizes from where it was to where the new layout puts it, instead of
jumping. First and Last boxes are measured, the difference is Inverted, and
the item Plays back to its new place."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def flip(first, last, p, ease=vb.ease_out_expo, stagger=0.0):
    """Every item's box at progress `p` (0 -> 1) between two layouts.

    `first` and `last` map a key to its `vb.Box` before and after the change.
    Returns `{key: (box, alpha)}`: a key in both moves and resizes from its
    first box to its last; a key only in `last` fades in at its last box, one
    only in `first` fades out at its first. `stagger` (0 -> <1) delays each
    later key, in `last`'s order then `first`'s, by that share of the run."""
    keys = list(last) + [k for k in first if k not in last]
    out = {}
    for i, k in enumerate(keys):
        start = stagger * i / max(1, len(keys) - 1)
        q = ease(vb.clamp01((p - start) / (1 - start))) if start < 1 else float(p >= 1)
        a, b = first.get(k), last.get(k)
        if a is not None and b is not None:
            out[k] = (vb.Box(*(u + (v - u) * q for u, v in zip(a, b))), 1.0)
        elif b is not None:
            out[k] = (b, vb.clamp01(q))
        else:
            out[k] = (a, 1 - vb.clamp01(q))
    return out


COLORS = (demo.ACCENT, demo.TEAL, '#f2b84b', '#7d8cf0', '#e27fb3', '#8fd16a')


def grid():
    """Before: six tiles in a 3 x 2 grid."""
    return {i: vb.Box(150 + (i % 3) * 230, 90 + (i // 3) * 190, 200, 160) for i in range(6)}


def hero(pick=2):
    """After: tile `pick` grown into a wide hero, the other five in a strip below."""
    out = {pick: vb.Box(150, 60, 660, 300)}
    rest = [i for i in range(6) if i != pick]
    for j, i in enumerate(rest):
        out[i] = vb.Box(150 + j * 136, 386, 116, 94)
    return out


def tile(cv, box, i, alpha=1.0):
    x, y, w, h = box
    r = min(w, h) * 0.12
    with cv.layer(opacity=alpha):
        cv.shadow(x, y, w, h, radius=r, dy=6, blur=18, color=(0, 0, 0, 0.45))
        cv.rect(x, y, w, h, COLORS[i], radius=r)
        demo.word(cv, str(i + 1), x + w / 2, y + h / 2, size=min(w, h) * 0.42, color=demo.BG)
    cv.mark(f'tile{i + 1}', x, y, w, h)


def draw(n, cv):
    boxes = flip(grid(), hero(), demo.phase(n, 0.7, 2.1), stagger=0.25)
    for i, (box, alpha) in sorted(boxes.items(), key=lambda kv: kv[0] == 2):  # the hero on top
        tile(cv, box, i, alpha)


CAPABILITY = Capability(
    id='layout-animation-flip',
    name='Layout animation (FLIP)',
    family='ui',
    group='Layout & lists',
    aliases=('FLIP animation', 'FLIP', 'shared layout animation', 'auto-animate layout',
             'magic move'),
    definition='When a layout changes, every element slides and resizes smoothly from its old spot to its '
               'new one instead of snapping there.',
    phrasings=('the cards rearrange themselves smoothly when one gets bigger',
               'animate the grid reflowing into its new layout',
               'items glide to their new positions when the list reorders'),
    related=('frame-by-frame-hand-drawn-animation', 'flipbook-sprite-animation', 'flip', 'tile-flip',
             'word-flip-in', 'reverse-playback'),
    api=('videobuilder.capabilities.ui.layout_animation_flip.flip',),
    demo=lambda: demo.film(draw),
)
