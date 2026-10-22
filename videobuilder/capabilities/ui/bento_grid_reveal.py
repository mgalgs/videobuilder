"""Bento Grid Reveal: the panels of an uneven dashboard-style grid -- one big
tile, a few tall and wide ones, some small -- arrive one after another, each
fading up and growing from a little under full size into its slot."""
import math

import videobuilder as vb
from videobuilder import Box, fr

from .. import _demo as demo
from ..schema import Capability


def bento_cells(box, gap=20):
    """Six tiles of an asymmetric grid filling `box`, largest first: a big
    feature tile top left, a small one beside it, a tall one down the right,
    then a tall, a small and a wide one along the bottom."""
    left, right = box.row(3 * fr, 1 * fr, gap=gap)
    top, bottom = left.column(1.4 * fr, 1 * fr, gap=gap)
    feature, small = top.row(2 * fr, 1 * fr, gap=gap)
    tall_r = right
    tall_l, rest = bottom.row(1 * fr, 2 * fr, gap=gap)
    small_b, wide = rest.column(1 * fr, 1 * fr, gap=gap)
    return [feature, small, tall_r, tall_l, small_b, wide]


def bento_reveal(cv, cells, p, draw_tile, stagger=0.55, start_scale=0.86, rise=14, order=None):
    """Draw the tiles in `cells` (Boxes) revealing at progress `p` (0 -> 1).
    Tiles enter in `order` (indexes into `cells`; default as listed), each
    over its own window; `stagger` in [0, 1] is how much of the whole run the
    start times are spread across (0: all at once). A tile fades up, rises
    `rise` px and scales from `start_scale` to 1 about its centre with a
    slight overshoot. `draw_tile(cv, i, box)` draws tile `i` at its rest size;
    it is called inside the tile's transform, so it needs no timing of its
    own, but gets `cv` as usual. A tile not started yet is not drawn."""
    order = list(range(len(cells))) if order is None else list(order)
    n = len(order)
    span = 1 - stagger if n > 1 else 1
    for k, i in enumerate(order):
        start = stagger * k / (n - 1) if n > 1 else 0
        t = vb.clamp01((p - start) / span)
        if t <= 0:
            continue
        box = cells[i]
        s = start_scale + (1 - start_scale) * vb.ease_out_back(t)
        dy = rise * (1 - vb.ease_out_expo(t))
        with cv.layer(opacity=vb.ease_out_expo(t), dx=box.cx * (1 - s), dy=box.cy * (1 - s) + dy, scale=s):
            draw_tile(cv, i, box)


# --- the demo: six dashboard panels, each with a simple glyph ---

PANEL = '#1f2530'
GOLD = '#f2b632'


def _panel(cv, b, color=PANEL):
    cv.shadow(b.x, b.y, b.w, b.h, radius=14, dy=6, blur=16, color=(0, 0, 0, 0.4))
    cv.rect(b.x, b.y, b.w, b.h, color, radius=14)


def _tile(cv, i, b):
    cx, cy = b.cx, b.cy
    if i == 0:  # feature: a progress ring
        _panel(cv, b, '#33407a')
        r = min(b.w, b.h) * 0.3
        cv.arc(cx, cy, r, 0, 2 * math.pi, '#4a5aa8', width=10)
        cv.arc(cx, cy, r, -math.pi / 2, math.pi * 1.25, '#8f9cff', width=10)
        demo.dot(cv, cx + r * math.cos(math.pi * 1.25), cy + r * math.sin(math.pi * 1.25), 8, demo.INK)
    elif i == 1:  # small: bar chart
        _panel(cv, b)
        bw, base = b.w * 0.12, b.y + b.h * 0.72
        for k, hh in enumerate((0.18, 0.3, 0.46)):
            cv.rect(cx - bw * 2 + k * bw * 1.5, base - b.h * hh, bw, b.h * hh, '#8f9cff', radius=4,
                    alpha=0.5 + 0.25 * k)
    elif i == 2:  # tall: a big gold dot over a caption bar
        _panel(cv, b, '#5a4a17')
        demo.dot(cv, cx, b.y + b.h * 0.38, b.w * 0.26, GOLD)
        cv.rect(cx - b.w * 0.25, b.y + b.h * 0.7, b.w * 0.5, 5, GOLD, radius=2.5, alpha=0.6)
    elif i == 3:  # tall: a rising curve
        _panel(cv, b)
        pts = [(b.x + b.w * (0.2 + 0.6 * u), b.y + b.h * (0.75 - 0.5 * (3 * u * u - 2 * u ** 3)))
               for u in (k / 24 for k in range(25))]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            cv.line(x0, y0, x1, y1, '#8f9cff', width=4)
        demo.dot(cv, *pts[-1], 7, demo.INK)
    elif i == 4:  # small: a toggle
        _panel(cv, b)
        tw, th = b.w * 0.5, b.h * 0.28
        cv.rect(cx - tw / 2, cy - th / 2, tw, th, '#8f9cff', radius=th / 2)
        demo.dot(cv, cx + tw / 2 - th / 2, cy, th * 0.36, demo.INK)
    else:  # wide: step dots
        _panel(cv, b)
        for k in range(4):
            demo.dot(cv, b.x + b.w * (0.2 + 0.2 * k), cy, min(b.h * 0.18, b.w * 0.07),
                     GOLD if k == 3 else '#4a5aa8')
    cv.mark(f'tile{i}', *b)


def draw(n, cv):
    grid = Box(0, 0, demo.W, demo.H).pad(60, 170)
    bento_reveal(cv, bento_cells(grid, gap=12), demo.phase(n, 0.3, 2.5), _tile)


CAPABILITY = Capability(
    id='bento-grid-reveal',
    name='Bento grid reveal',
    family='ui',
    group='Layout & lists',
    aliases=('tile grid entrance', 'bento stagger', 'bento box layout reveal'),
    definition='The panels of an uneven, mixed-size grid appear one after another, each fading in '
               'and growing slightly into its slot until the whole layout is filled.',
    phrasings=('build up the dashboard cards one at a time in a bento layout',
               'have the feature grid tiles pop in with a stagger',
               'animate the mixed-size boxes appearing one by one'),
    related=('swiss-grid-slide', 'tile-grid-title-reveal', 'tile-flip', 'grid-diagonal-stagger',
             'hexagon-tile-reveal', 'truchet-tiles'),
    api=('videobuilder.capabilities.ui.bento_grid_reveal.bento_reveal',
         'videobuilder.capabilities.ui.bento_grid_reveal.bento_cells'),
    demo=lambda: demo.film(draw),
)
