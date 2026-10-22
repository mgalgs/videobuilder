"""Waffle Chart Fill: a grid of equal squares, each standing for one share of
the whole, lights up square by square in reading order until the coloured
squares count out the value."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def waffle_order(cols, rows, start='bottom'):
    """The (col, row) cells of a `cols` x `rows` grid in fill order: row by
    row, left to right, from the bottom row up (`start='bottom'`) or from the
    top row down (`start='top'`)."""
    ys = range(rows - 1, -1, -1) if start == 'bottom' else range(rows)
    return [(c, r) for r in ys for c in range(cols)]


def waffle_chart(cv, x, y, w, h, filled, cols=10, rows=10, color=demo.ACCENT, empty=demo.LINE, gap=0.18,
                 start='bottom', pop=1.6):
    """Draw a waffle chart in the box (x, y, w, h) with `filled` squares lit
    (a float: 37.4 means 37 lit and the 38th part-way in). Each square is
    one of `cols * rows` equal shares; animate `filled` from 0 to the value
    to fill it. A square fading in grows from 60% with a small overshoot
    over the last `pop` squares, so the leading edge reads as moving. `gap`
    is the space between squares as a fraction of a cell. Returns the cell
    size."""
    cell = min(w / cols, h / rows)
    side = cell * (1 - gap)
    ox, oy = x + (w - cell * cols) / 2, y + (h - cell * rows) / 2
    radius = side * 0.18
    for i, (c, r) in enumerate(waffle_order(cols, rows, start)):
        cx, cy = ox + (c + 0.5) * cell, oy + (r + 0.5) * cell
        cv.rect(cx - side / 2, cy - side / 2, side, side, empty, radius=radius)
        k = vb.clamp01((filled - i) / pop) if pop > 0 else float(filled > i)
        if k <= 0:
            continue
        s = side * (0.6 + 0.4 * vb.ease_out_back(k))
        cv.rect(cx - s / 2, cy - s / 2, s, s, color, radius=radius * s / side, alpha=min(1.0, k * 1.5))
    return cell


CHARTS = (('North', 72, demo.ACCENT), ('Central', 45, demo.TEAL), ('South', 28, demo.INK))


def draw(n, cv):
    size, gap = 250, 60
    left = (demo.W - (3 * size + 2 * gap)) / 2
    top = demo.H / 2 - size / 2 + 40
    demo.word(cv, '1 square = 1%', demo.W / 2, 60, size=22, color=demo.MUTED, weight=600)
    for i, (label, value, color) in enumerate(CHARTS):
        p = vb.ease_in_out_quart(demo.phase(n, 0.4 + 0.15 * i, 2.3 + 0.15 * i))
        filled = value * p
        x = left + i * (size + gap)
        waffle_chart(cv, x, top, size, size, filled, color=color)
        cv.mark(f'waffle-{label.lower()}', x, top, size, size)
        demo.word(cv, label, x + 50, top - 34, size=26, color=demo.INK, weight=700)
        demo.word(cv, f'{round(filled)}%', x + size - 40, top - 34, size=32, color=color, weight=800)


CAPABILITY = Capability(
    id='waffle-chart-fill',
    name='Waffle chart fill',
    family='broadcast',
    group='Charts',
    aliases=('waffle grid fill', 'square unit chart', 'waffle chart', 'square pie chart'),
    definition='A ten-by-ten grid of small squares colours in one square at a time, each worth an equal '
               'slice, until the lit squares add up to the figure being shown.',
    phrasings=('colour in a grid of 100 squares to show a percentage',
               'show the stat as little boxes filling up one by one',
               'a block grid that lights up to 72 out of 100'),
    related=('choropleth-fill', 'shape-fill-sweep', 'percentage-fill-bar', 'marching-squares-contour',
             'liquid-fill-level', 'scale-tile-wave'),
    api=('videobuilder.capabilities.broadcast.waffle_chart_fill.waffle_chart',
         'videobuilder.capabilities.broadcast.waffle_chart_fill.waffle_order'),
    demo=lambda: demo.film(draw),
)
