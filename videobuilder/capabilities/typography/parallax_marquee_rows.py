"""Parallax marquee rows: stacked lines of repeated type, each sliding
sideways forever, neighbours in opposite directions and at different speeds.
Each row is a `parallax.Layer` whose tile is one copy of its text plus a gap,
so the wrap-around repeat comes from `parallax.draw`."""
from dataclasses import dataclass

import videobuilder as vb
from videobuilder import parallax

from .. import _demo as demo
from ..schema import Capability


@dataclass(frozen=True)
class Row:
    """One marquee row: `text` in `font`, its top at `y`, sliding `speed` px
    per second (positive runs right to left, negative left to right), with
    `gap` px between repeats, already `offset` px along at 0 s."""
    text: str
    font: object
    y: float
    speed: float
    color: object = demo.INK
    alpha: float = 1.0
    gap: float = 80
    offset: float = 0


def row_layer(row):
    """`row` as a `parallax.Layer`: one tile is the text and its gap, at depth
    1, so it moves exactly as far as the pan `draw_marquee_rows` gives it."""
    width = vb.text.measure(row.text, row.font) + row.gap

    def tile(cv, x):
        vb.text.draw(cv, [row.text], row.font, x, row.y, row.color, alpha=row.alpha)
    return parallax.Layer(1.0, width, tile)


def draw_marquee_rows(cv, rows, t):
    """Draw every row of `rows` at `t` seconds, each tiled across the full
    frame width and shifted by its own speed. For a seamless loop over a
    film of `T` seconds, pick speeds so `speed * T` is a whole number of
    each row's tile widths."""
    for r in rows:
        parallax.draw(cv, [row_layer(r)], r.speed * t + r.offset)


def rows_for(text, count=5, size=None, top=None, spacing=1.35, speeds=(260, 170, 320, 140, 230)):
    """`count` rows of `text` stacked from `top` (default: centred in the
    frame), alternating direction, bright and `size` px (default: 12% of the
    frame height) on even rows, smaller and dimmer on odd ones, so the stack
    reads as near and far layers."""
    size = size or round(demo.H * 0.12)
    lh = size * spacing
    top = (demo.H - lh * count) / 2 + (lh - size) / 2 if top is None else top
    out = []
    for i in range(count):
        near = i % 2 == 0
        f = demo.font(size if near else round(size * 0.8), 800)
        out.append(Row(text, f, top + i * lh + (0 if near else size * 0.1),
                       speeds[i % len(speeds)] * (1 if near else -1),
                       color=demo.INK if near else demo.MUTED, alpha=1.0 if near else 0.75,
                       offset=i * size * 1.7))
    return tuple(out)


ROWS = rows_for('MOTION', speeds=(240, 130, 300, 110, 200))


def draw(n, cv):
    draw_marquee_rows(cv, ROWS, n / demo.FPS)
    cv.mark('rows', 0, ROWS[0].y, demo.W, ROWS[-1].y + ROWS[-1].font.size - ROWS[0].y)


CAPABILITY = Capability(
    id='parallax-marquee-rows',
    name='Parallax marquee rows',
    family='typography',
    group='Looping and marquee',
    aliases=('opposing marquee', 'multi-row scroll type', 'alternating marquee'),
    definition='Stacked lines of repeating words slide sideways without end, each line '
               'heading the opposite way to its neighbour and at its own pace.',
    phrasings=('rows of text scrolling past in opposite directions',
               'a wall of repeating words where every line drifts at a different speed',
               'layered ticker lines going left and right'),
    related=('scroll-parallax-layers', 'infinite-marquee', 'parallax-slide', 'smooth-scroll-inertia',
             'scroll-snap-sections', 'scroll-velocity-skew'),
    api=('videobuilder.capabilities.typography.parallax_marquee_rows.draw_marquee_rows',
         'videobuilder.capabilities.typography.parallax_marquee_rows.Row',
         'videobuilder.capabilities.typography.parallax_marquee_rows.rows_for',
         'videobuilder.parallax.draw'),
    demo=lambda: demo.film(draw),
)
