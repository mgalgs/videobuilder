"""Chart Type Morph: the same data marks reshape from one chart form into
another -- here each bar of a bar chart bends into its wedge of a pie, so the
viewer can follow every value across the change."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ...looks import kit as looks

COLORS = (demo.ACCENT, demo.TEAL, '#f2b84b', '#7a8cff', '#c77dff')


def _edge(a, b, k):
    """`k` evenly spaced points from a to b, a included, b left out."""
    return [(a[0] + (b[0] - a[0]) * i / k, a[1] + (b[1] - a[1]) * i / k) for i in range(k)]


def bar_outline(x, base, w, h, k=24):
    """A bar from `x` (left) and `base` (bottom), `w` wide and `h` tall, as a
    closed outline of 4 * `k` points: left side up, top, right side down,
    bottom -- the same order as `wedge_outline`, so the two morph cleanly."""
    bl, tl, tr, br = (x, base), (x, base - h), (x + w, base - h), (x + w, base)
    return _edge(bl, tl, k) + _edge(tl, tr, k) + _edge(tr, br, k) + _edge(br, bl, k)


def wedge_outline(cx, cy, r, a0, a1, k=24):
    """A pie wedge about (cx, cy), radius `r`, from angle `a0` to `a1`
    (radians, clockwise from twelve o'clock), as 4 * `k` points matching
    `bar_outline`: out along `a0`, round the arc, back in along `a1`, and the
    bottom edge collapsed onto the centre."""
    at = lambda a, rr: (cx + rr * math.sin(a), cy - rr * math.cos(a))  # noqa: E731
    up = [at(a0, r * i / k) for i in range(k)]
    arc = [at(a0 + (a1 - a0) * i / k, r) for i in range(k)]
    down = [at(a1, r * (k - i) / k) for i in range(k)]
    return up + arc + down + [(cx, cy)] * k


def lerp_outline(a, b, p):
    """Two outlines of equal length blended point by point at `p` (0 -> 1)."""
    return [(x0 + (x1 - x0) * p, y0 + (y1 - y0) * p) for (x0, y0), (x1, y1) in zip(a, b)]


def bar_to_pie(values, p, plot, center, radius, gap=0.35, stagger=0.4, ease=vb.ease_in_out_quart, k=24,
               lift=20):
    """The marks of a bar chart of `values` morphing into a pie at progress
    `p` (0 -> 1). Bars sit in the `plot` Box on its bottom edge, scaled so the
    largest fills its height, `gap` of each column left empty; the pie is
    centred on `center` with `radius`, slices clockwise from twelve o'clock in
    the same order. Mark `i` starts after `stagger * i / (n - 1)` of the run.
    `lift` raises the bar's label above its top.
    Returns one `(outline, anchor, q)` per value: its blended outline, a
    point to hang its label on (bar top -> wedge middle) and its own eased
    progress."""
    n, top, total = len(values), max(values), sum(values)
    col = plot.w / n
    cx, cy = center
    out, a = [], 0.0
    for i, v in enumerate(values):
        span = 2 * math.pi * v / total
        q = vb.clamp01((p - stagger * i / max(1, n - 1)) / (1 - stagger)) if stagger < 1 else p
        q = ease(q)
        bw, bh = col * (1 - gap), plot.h * v / top
        bx, base = plot.x + col * i + col * gap / 2, plot.y + plot.h
        shape = lerp_outline(bar_outline(bx, base, bw, bh, k), wedge_outline(cx, cy, radius, a, a + span, k), q)
        mid = a + span / 2
        bar_pt = (bx + bw / 2, base - bh - lift)
        pie_pt = (cx + radius * 0.66 * math.sin(mid), cy - radius * 0.66 * math.cos(mid))
        out.append((shape, lerp_outline([bar_pt], [pie_pt], q)[0], q))
        a += span
    return out


def draw_bar_to_pie(cv, values, p, plot, center, radius, colors=COLORS, labels=True, font=None, **kw):
    """Draw `bar_to_pie` marks filled in `colors` (cycled), each labelled
    with its value unless `labels` is false. `kw` goes to `bar_to_pie`.
    Returns the marks."""
    marks = bar_to_pie(values, p, plot, center, radius, **kw)
    for i, (shape, _, _) in enumerate(marks):
        looks.fill(cv, shape, colors[i % len(colors)], outline=demo.BG, width=3)
    if labels:
        f = font or demo.mono(22, 700)
        for v, (_, (x, y), _) in zip(values, marks):
            demo.word(cv, str(v), x, y, font=f, color=demo.INK)
    return marks


VALUES = (42, 68, 30, 55, 24)
PLOT = vb.Box(demo.W / 2 - 300, 140, 600, 300)


def draw(n, cv):
    p = demo.phase(n, 0.7, 2.3)
    axis = 1 - vb.clamp01(p * 3)
    if axis > 0:
        demo.floor(cv, PLOT.bottom, demo.LINE)
        f = demo.font(20, 700)
        for i, name in enumerate('ABCDE'):
            demo.word(cv, name, PLOT.x + PLOT.w / 5 * (i + 0.5), PLOT.bottom + 24, font=f,
                      color=demo.MUTED, alpha=axis)
    draw_bar_to_pie(cv, VALUES, p, PLOT, (demo.W / 2, demo.H / 2), 200)
    cv.mark('chart', demo.W / 2 - 300, 60, 600, 420)


CAPABILITY = Capability(
    id='chart-type-morph',
    name='Chart type morph',
    family='broadcast',
    group='Charts',
    aliases=('chart type transition', 'bar-to-pie morph', 'chart morph'),
    definition='Each mark of a chart reshapes in place into the matching mark of a different chart type, '
               'so bars bend into pie slices while the data stays traceable.',
    phrasings=('turn the bar chart into a pie chart without cutting',
               'the bars curl round and become slices of a pie',
               'animate the graph changing from one kind of chart to another'),
    related=('text-to-shape-morph', 'shape-morph', 'play-pause-morph', 'icon-state-morph',
             'variable-font-weight-animation', 'letter-morph'),
    api=('videobuilder.capabilities.broadcast.chart_type_morph.bar_to_pie',
         'videobuilder.capabilities.broadcast.chart_type_morph.draw_bar_to_pie'),
    demo=lambda: demo.film(draw),
)
