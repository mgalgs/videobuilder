"""Box plot draw: a box-and-whisker chart builds itself -- the median rule
appears, the box opens out from it to the quartiles, the whiskers run out to
the extremes and their caps snap on, then any outliers pop in."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def _span(p, a, b):
    return vb.clamp01((p - a) / (b - a))


def draw_box_plot(cv, cx, stats, p, y_of, width=90, color=demo.TEAL, ink=demo.INK, line=4,
                  outliers=(), ease=vb.ease_out_expo):
    """One vertical box plot centred on `cx`, drawn to progress `p` (0 -> 1).
    `stats` is (low, q1, median, q3, high) in data units and `y_of(v)` maps a
    value to a screen y. In order: the median rule grows out from the centre,
    the box opens up and down from the median to q1 and q3, the whiskers run
    out from the box to low and high, their caps widen, and each value in
    `outliers` pops in as a ring. Returns the Box the finished plot covers."""
    lo, q1, ym, q3, hi = (y_of(v) for v in stats)
    rule = ease(_span(p, 0.0, 0.25))
    box = ease(_span(p, 0.15, 0.55))
    whisk = ease(_span(p, 0.45, 0.8))
    cap = vb.ease_out_back(_span(p, 0.72, 0.9))
    half = width / 2
    if whisk > 0:
        top, bot = q3 + (hi - q3) * whisk, q1 + (lo - q1) * whisk
        cv.line(cx, q3, cx, top, ink, width=line)
        cv.line(cx, q1, cx, bot, ink, width=line)
        if cap > 0:
            c = half * 0.55 * cap
            cv.line(cx - c, hi, cx + c, hi, ink, width=line)
            cv.line(cx - c, lo, cx + c, lo, ink, width=line)
    if box > 0:
        y0, y1 = ym + (q3 - ym) * box, ym + (q1 - ym) * box
        cv.rect(cx - half, y0, width, y1 - y0, color, alpha=0.85)
        cv.outline(cx - half, y0, width, y1 - y0, ink, width=line)
    if rule > 0:
        r = half * rule
        cv.line(cx - r, ym, cx + r, ym, ink, width=line + 2)
    for i, v in enumerate(outliers):
        q = vb.ease_out_back(_span(p, 0.88 + 0.04 * i, 1.0))
        if q > 0:
            cv.arc(cx, y_of(v), 6 * q, 0, 2 * math.pi, ink, width=max(1, line - 1))
    ys = [y_of(v) for v in (*stats, *outliers)]
    return vb.Box(cx - half, min(ys) - 10, width, max(ys) - min(ys) + 20)


def box_plot_draw(cv, plots, p, x0, x1, y_of, stagger=0.45, **kw):
    """A row of box plots spread evenly between `x0` and `x1`, each drawn by
    `draw_box_plot` in turn: `plots` is a list of `stats` tuples or
    `(stats, outliers)` pairs, starts are spread over the first `stagger` of
    `p`, and `kw` passes through. Returns each plot's Box."""
    n = len(plots)
    out = []
    for i, entry in enumerate(plots):
        stats, outs = entry if len(entry) == 2 else (entry, ())
        start = stagger * i / max(1, n - 1)
        q = vb.clamp01((p - start) / (1 - stagger))
        cx = x0 + (x1 - x0) * (i + 0.5) / n
        out.append(draw_box_plot(cv, cx, stats, q, y_of, outliers=outs, **kw))
    return out


PLOTS = (((22, 38, 47, 60, 78), (90,)),
         ((30, 52, 61, 70, 84), ()),
         ((12, 26, 35, 44, 58), (4, 74)),
         ((40, 55, 66, 74, 88), ()))
LEFT, RIGHT, TOP, BOTTOM = 190, 800, 70, 450


def y_of(v):
    return BOTTOM - (BOTTOM - TOP) * v / 100


def draw(n, cv):
    axes = demo.phase(n, 0.0, 0.4)
    cv.line(LEFT, BOTTOM, LEFT + (RIGHT - LEFT) * axes, BOTTOM, demo.MUTED, width=2)
    cv.line(LEFT, BOTTOM, LEFT, BOTTOM - (BOTTOM - TOP) * axes, demo.MUTED, width=2)
    f = demo.mono(15, 500)
    for v in (0, 25, 50, 75, 100):
        if axes >= v / 100:
            cv.line(LEFT, y_of(v), RIGHT, y_of(v), demo.LINE, width=1, alpha=0.6)
            w, h = vb.text.block_size([str(v)], f)
            vb.text.draw(cv, [str(v)], f, LEFT - 12 - w, y_of(v) - h / 2, demo.MUTED)
    boxes = box_plot_draw(cv, PLOTS, demo.phase(n, 0.3, 2.6), LEFT + 20, RIGHT, y_of, width=76, line=3,
                          color=demo.TEAL)
    for i, b in enumerate(boxes):
        cv.mark(f'plot{i}', *b)
    for i, label in enumerate(('North', 'South', 'East', 'West')):
        cx = LEFT + 20 + (RIGHT - LEFT - 20) * (i + 0.5) / len(PLOTS)
        demo.word(cv, label, cx, BOTTOM + 26, size=18, color=demo.MUTED, weight=700, alpha=axes)


TECHNIQUE = Technique(
    id='box-plot-draw',
    name='Box plot draw',
    family='broadcast',
    group='Charts',
    aliases=('box-and-whisker draw-on', 'whisker plot build', 'animated box plot'),
    definition='A box-and-whisker chart assembles on screen: each median line appears, the box opens '
               'out to the quartiles, and the whiskers stretch to the extremes before outliers pop in.',
    phrasings=('animate a box and whisker chart drawing itself in',
               'show the spread of each group as box plots that grow out from the median',
               'build the quartile chart piece by piece, whiskers last'),
    related=('flowchart-build', 'box-wipe', 'pencil-sketch', 'letterbox', 'org-chart-grow',
             'spiral-expansion-draw'),
    api=('videobuilder.techniques.broadcast.box_plot_draw.box_plot_draw',
         'videobuilder.techniques.broadcast.box_plot_draw.draw_box_plot'),
    demo=lambda: demo.film(draw),
)
