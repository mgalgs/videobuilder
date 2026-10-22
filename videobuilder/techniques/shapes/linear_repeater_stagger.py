"""Linear Repeater Stagger: a row of copies of one shape all make the same
move, each a fixed beat behind its neighbour, so the move ripples down the
row like an echo."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def stagger(p, i, count, spread=0.5):
    """Copy `i`'s own progress (0 -> 1) of `count` copies at overall progress
    `p`. The first copy starts at 0 and the last at `spread`; each runs for
    `1 - spread` of the whole, so every copy finishes by `p = 1`."""
    if count <= 1:
        return vb.clamp01(p)
    span = 1 - spread
    return vb.clamp01((p - spread * i / (count - 1)) / span) if span > 0 else float(p >= spread * i / (count - 1))


def linear_repeater(cv, draw_copy, count, x, y, dx, p, dy=0.0, spread=0.5, ease=vb.ease_in_out_quart):
    """Draw `count` copies laid out from (x, y) in steps of (dx, dy), each
    with the same motion offset in time: `draw_copy(cv, i, cx, cy, q)` draws
    copy `i` at its slot (cx, cy) with its own eased progress `q`. `spread`
    is the share of `p` the delays take up (see `stagger`)."""
    for i in range(count):
        draw_copy(cv, i, x + i * dx, y + i * dy, ease(stagger(p, i, count, spread)))


SIZE, COUNT, GAP, RISE = 56, 8, 86, 170


def _tile(cv, i, cx, cy, q):
    cy -= RISE * q
    c = cv.ctx
    c.save()
    c.translate(cx, cy)
    c.rotate(math.pi / 2 * q)  # a quarter turn on the way up, so it lands square again
    cv.rect(-SIZE / 2, -SIZE / 2, SIZE, SIZE, demo.ACCENT, radius=11)
    c.restore()


def draw(n, cv):
    x0 = (demo.W - GAP * (COUNT - 1)) / 2
    y0 = demo.H / 2 + RISE / 2
    for i in range(COUNT):  # a faint mark under each copy's starting slot
        demo.dot(cv, x0 + i * GAP, y0 + SIZE / 2 + 18, r=4, color=demo.MUTED, alpha=0.5)
    linear_repeater(cv, _tile, COUNT, x0, y0, GAP, demo.phase(n, 0.4, 2.6), spread=0.55)
    cv.mark('row', x0 - SIZE / 2, y0 - RISE - SIZE / 2, GAP * (COUNT - 1) + SIZE, RISE + SIZE)


TECHNIQUE = Technique(
    id='linear-repeater-stagger',
    name='Linear repeater stagger',
    family='shapes',
    group='Repeaters & patterns',
    aliases=('echo repeater', 'staggered copies', 'offset duplicates'),
    definition='A line of identical shapes all perform the same move, each starting a beat after the one '
               'before, so the motion rolls along the row.',
    phrasings=('a row of squares that hop up one after another like a wave',
               'duplicate the shape across the screen and offset each copy\'s timing',
               'the same animation on every copy, cascading down the line'),
    related=('linear-stagger', 'wave-stagger', 'grid-diagonal-stagger', 'proximity-stagger',
             'frame-delay-echo', 'eased-stagger'),
    api=('videobuilder.techniques.shapes.linear_repeater_stagger.linear_repeater',
         'videobuilder.techniques.shapes.linear_repeater_stagger.stagger'),
    demo=lambda: demo.film(draw),
)
