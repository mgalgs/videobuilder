"""Scatter Plot Point Appear: the axes are already there; the data points pop
in one after another, each growing from nothing with a little overshoot and a
faint ring, until the whole cloud shows the shape of the data."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def point_progress(i, count, p, span=0.22):
    """Progress 0 -> 1 of point `i` of `count` at overall progress `p`. Points
    start evenly staggered; each takes `span` of the whole reveal, so several
    are mid-pop at once and the last lands exactly at `p` = 1."""
    span = min(1.0, max(span, 1.0 / max(count, 1)))
    start = 0.0 if count <= 1 else i / (count - 1) * (1 - span)
    return vb.clamp01((p - start) / span)


def draw_scatter_appear(cv, points, plot, p, x_range=(0, 1), y_range=(0, 1), r=11, color=demo.ACCENT,
                        order='x', span=0.22, ring=True):
    """Draw scatter `points` ((x, y) in data units) into the `plot` Box at
    reveal progress `p` (0 -> 1). They appear one at a time in `order`: 'x'
    (left to right), 'y' (bottom up), 'given' (list order) or 'random'
    (shuffled, seeded, so the same every frame). Each grows from nothing with
    an overshoot, fading up as it does; `ring` adds a ripple that spreads and
    fades as it lands. Returns the screen positions, in the order given."""
    (x0, x1), (y0, y1) = x_range, y_range
    screen = [(plot.x + (x - x0) / (x1 - x0) * plot.w, plot.bottom - (y - y0) / (y1 - y0) * plot.h)
              for x, y in points]
    idx = list(range(len(points)))
    if order == 'x':
        idx.sort(key=lambda k: points[k][0])
    elif order == 'y':
        idx.sort(key=lambda k: points[k][1])
    elif order == 'random':
        random.Random(len(points)).shuffle(idx)
    for rank, k in enumerate(idx):
        q = point_progress(rank, len(points), p, span)
        if q <= 0:
            continue
        sx, sy = screen[k]
        grow = vb.ease_out_back(vb.clamp01(q / 0.7))
        if ring and 0.3 < q < 1:
            t = (q - 0.3) / 0.7
            cv.arc(sx, sy, r * (1 + 2.2 * vb.ease_out_expo(t)), 0, 2 * math.pi, color, width=2,
                   alpha=0.55 * (1 - t))
        cv.sector(sx, sy, max(0.1, r * grow), 0, 2 * math.pi, color, alpha=vb.clamp01(q / 0.35))
    return screen


def _data(n=30, seed=4):
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        x = rng.uniform(0.6, 9.6)
        out.append((x, max(0.4, min(9.6, 1.2 + 0.78 * x + rng.gauss(0, 1.1)))))
    return out


DATA = _data()


def draw(n, cv):
    plot = vb.Box(demo.W * 0.16, demo.H * 0.2, demo.W * 0.7, demo.H * 0.62)
    tick = demo.font(13, 600)
    for k in range(6):
        y = plot.bottom - k / 5 * plot.h
        cv.line(plot.x, y, plot.right, y, demo.LINE, width=1, alpha=0.6)
        vb.text.draw(cv, [str(k * 20)], tick, plot.x - 44, y - 8, demo.MUTED, align='right', width=34)
    for k in range(6):
        x = plot.x + k / 5 * plot.w
        vb.text.draw(cv, [str(k * 20)], tick, x - 30, plot.bottom + 10, demo.MUTED, align='center', width=60)
    cv.line(plot.x, plot.y, plot.x, plot.bottom, demo.MUTED, width=2)
    cv.line(plot.x, plot.bottom, plot.right, plot.bottom, demo.MUTED, width=2)
    demo.word(cv, 'Ad spend vs. sales', demo.W / 2, demo.H * 0.1, size=26, color=demo.INK, weight=700)
    draw_scatter_appear(cv, DATA, plot, demo.phase(n, 0.3, 2.5), x_range=(0, 10), y_range=(0, 10),
                        r=7, span=0.14)
    cv.mark('plot', *plot)


TECHNIQUE = Technique(
    id='scatter-plot-point-appear',
    name='Scatter plot point appear',
    family='broadcast',
    group='Charts',
    aliases=('scatter reveal', 'dot plot fade-in', 'scatter points pop in'),
    definition='On an empty pair of axes, the dots of a scatter plot pop into view one after another '
               'until the full cloud of data is showing.',
    phrasings=('make the scatter plot dots appear one by one',
               'pop the data points onto the chart in sequence',
               'build up the scatter chart point by point so the trend emerges'),
    related=('dot-density-map', 'point-cloud-reveal', 'ink-splash-spread', 'diffraction-spikes',
             'halftone-dot-scaling', 'cursor-particle-trail'),
    api=('videobuilder.techniques.broadcast.scatter_plot_point_appear.draw_scatter_appear',
         'videobuilder.techniques.broadcast.scatter_plot_point_appear.point_progress'),
    demo=lambda: demo.film(draw),
)
