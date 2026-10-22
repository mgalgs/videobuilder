"""Staggered cascade reveal: a set of items arrives one after another, each
starting a beat after the one before, rising a little and fading in, so the
group fills in as a ripple rather than all at once."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def cascade(p, count, spread=0.6, ease=vb.ease_out_quint):
    """Per-item progress (0 -> 1 each, eased) for `count` items at overall
    progress `p`. Item starts are spaced evenly across the first `spread` of
    the run, and each item takes the remaining `1 - spread` to arrive, so the
    first starts at 0 and the last lands at 1."""
    p = vb.clamp01(p)
    span = 1 - spread
    step = spread / max(count - 1, 1)
    return [ease(vb.clamp01((p - i * step) / span)) for i in range(count)]


def reveal(cv, item, q, rise=40.0):
    """Draw one cascading item at its own progress `q`: `item(cv)` drawn in a
    layer that rises `rise` px into place and fades from 0 to 1. Nothing is
    drawn before it starts."""
    if q <= 0:
        return
    with cv.layer(opacity=q, dy=rise * (1 - q)):
        item(cv)


COLS, ROWS = 3, 2
CW, CH, GAP = 220, 136, 32


def draw(n, cv):
    gw, gh = COLS * CW + (COLS - 1) * GAP, ROWS * CH + (ROWS - 1) * GAP
    x0, y0 = (demo.W - gw) / 2 + CW / 2, (demo.H - gh) / 2 + CH / 2 + 30
    demo.word(cv, 'Your tools', demo.W / 2, y0 - CH / 2 - 60, size=40)
    colors = (demo.ACCENT, demo.TEAL)
    qs = cascade(demo.phase(n, 0.35, 2.35), COLS * ROWS, spread=0.65)
    for i, q in enumerate(qs):
        r, c = divmod(i, COLS)
        cx, cy = x0 + c * (CW + GAP), y0 + r * (CH + GAP)
        reveal(cv, lambda cv, cx=cx, cy=cy, i=i: demo.card(cv, cx, cy, w=CW, h=CH, color=colors[i % 2]), q)


TECHNIQUE = Technique(
    id='staggered-cascade-reveal',
    name='Staggered cascade reveal',
    family='ui',
    group='Scroll',
    aliases=('sequenced reveal', 'stagger on scroll', 'staggered entrance'),
    definition='The items of a list or grid come into view in turn, each one rising and fading in '
               'a moment after the one before it.',
    phrasings=('bring the cards in one after another instead of all at once',
               'have the grid ripple into view tile by tile',
               'as the section appears, stagger the items in with a small delay each'),
    related=('dropdown-stagger-reveal', 'uncover', 'linear-stagger', 'small-multiples-cascade', 'roll-up',
             'stacked-card-reveal'),
    api=('videobuilder.techniques.ui.staggered_cascade_reveal.cascade',
         'videobuilder.techniques.ui.staggered_cascade_reveal.reveal'),
    demo=lambda: demo.film(draw),
)
