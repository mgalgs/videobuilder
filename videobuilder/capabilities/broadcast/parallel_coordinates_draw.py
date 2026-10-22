"""Parallel coordinates draw: a row of vertical value axes, then one polyline
per record that strokes across them left to right, the records following
each other in a staggered sequence."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def record_points(values, box, lo=0.0, hi=100.0):
    """The polyline for one record: `values[i]` on axis `i`, the axes spread
    evenly across `box` (left edge to right edge), `lo` at its bottom and `hi`
    at its top."""
    n = len(values)
    out = []
    for i, v in enumerate(values):
        x = box.x + box.w * (i / (n - 1) if n > 1 else 0.5)
        t = vb.clamp01((v - lo) / (hi - lo))
        out.append((x, box.y + box.h * (1 - t)))
    return out


def record_progress(p, count, i, overlap=0.6):
    """How far record `i` of `count` has drawn (0 -> 1) at overall progress
    `p`. Each record takes the same share of time; `overlap` (0..1) lets the
    next one start before the previous has finished."""
    if count <= 1:
        return vb.clamp01(p)
    span = 1 / (count - (count - 1) * overlap)
    start = i * span * (1 - overlap)
    return vb.clamp01((p - start) / span)


def draw_axes(cv, box, count, labels=(), color=demo.MUTED, ticks=5, font=None, alpha=1.0):
    """`count` vertical axes evenly across `box`, with `ticks` small marks on
    each and an optional label above. Returns their x positions."""
    f = font or demo.mono(20, 700)
    xs = [box.x + box.w * (i / (count - 1) if count > 1 else 0.5) for i in range(count)]
    for i, x in enumerate(xs):
        cv.line(x, box.y, x, box.y + box.h, color, width=2, alpha=alpha)
        for k in range(ticks + 1):
            y = box.y + box.h * k / ticks
            cv.line(x - 5, y, x + 5, y, color, width=2, alpha=alpha * 0.7)
        if i < len(labels):
            w, h = vb.text.block_size([labels[i]], f)
            vb.text.draw(cv, [labels[i]], f, x - w / 2, box.y - h - 14, demo.INK, alpha=alpha)
    return xs


def draw_parallel_coordinates(cv, records, box, p, colors=(demo.ACCENT, demo.TEAL), lo=0.0, hi=100.0,
                              width=3, alpha=0.9, overlap=0.6, dots=True):
    """Draw `records` (each a sequence of one value per axis) as polylines
    across the axes in `box`, at overall progress `p` (0 -> 1): record `i`
    strokes in from the first axis to the last on its own slot of time
    (`record_progress`), coloured `colors[i % len(colors)]`, with a dot on
    each axis it has reached. Draw the axes first with `draw_axes`."""
    for i, values in enumerate(records):
        q = vb.ease_in_out_quart(record_progress(p, len(records), i, overlap))
        if q <= 0:
            continue
        color = colors[i % len(colors)]
        pts = record_points(values, box, lo, hi)
        shown = vb.paths.reveal(pts, q)
        vb.paths.draw(cv, shown, color, width=width, alpha=alpha)
        if dots:
            reached = vb.paths.length(shown) + 0.5
            for k, (x, y) in enumerate(pts):
                if vb.paths.length(pts[:k + 1]) <= reached:
                    demo.dot(cv, x, y, r=5, color=color)


RECORDS = (
    (42, 86, 58, 30), (68, 48, 82, 60), (55, 74, 40, 88), (87, 62, 70, 45),
    (30, 40, 90, 72), (74, 92, 52, 64), (49, 28, 64, 80), (80, 66, 34, 52),
)


def draw(n, cv):
    box = vb.Box(demo.W * 0.16, demo.H * 0.22, demo.W * 0.68, demo.H * 0.66)
    draw_axes(cv, box, 4, labels=('SPEED', 'POWER', 'RANGE', 'COST'), alpha=demo.phase(n, 0.0, 0.4))
    draw_parallel_coordinates(cv, RECORDS, box, demo.phase(n, 0.4, 2.6))
    cv.mark('chart', *box)


CAPABILITY = Capability(
    id='parallel-coordinates-draw',
    name='Parallel coordinates draw',
    family='broadcast',
    group='Charts',
    aliases=('parallel plot', 'multi-axis line', 'parallel coordinates'),
    definition='Several upright value axes stand side by side and each data record strokes on as a line '
               'zig-zagging across them, one record after another.',
    phrasings=('draw each data row as a line across a set of vertical axes, one after the other',
               'a multi-axis chart where the lines sweep in across the columns in turn',
               'animate a parallel plot building up record by record'),
    related=('speed-lines', 'isometric-view', 'dimension-line-annotation', 'streamlines', 'pencil-sketch',
             'line-weave'),
    api=('videobuilder.capabilities.broadcast.parallel_coordinates_draw.draw_parallel_coordinates',
         'videobuilder.capabilities.broadcast.parallel_coordinates_draw.draw_axes',
         'videobuilder.capabilities.broadcast.parallel_coordinates_draw.record_points',
         'videobuilder.paths.reveal'),
    demo=lambda: demo.film(draw),
)
