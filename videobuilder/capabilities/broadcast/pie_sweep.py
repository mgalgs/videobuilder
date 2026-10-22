"""Pie Sweep: a pie (or donut) chart that draws itself in with one clockwise
sweep from twelve o'clock, like a clock hand painting the slices in order,
each slice's share label appearing once its wedge is complete."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

TOP = -math.pi / 2   # twelve o'clock; canvas angles run clockwise


def pie_sweep(cv, cx, cy, r, values, colors, p, hole=0.0, gap=0.0, background=demo.BG, labels=True,
              font=None, label_color=demo.INK):
    """Draw a pie chart of `values` (any positive numbers, in order clockwise
    from twelve o'clock) centred at (cx, cy) with radius `r`, swept in to
    progress `p` (0 -> 1; ease it yourself). `colors` cycles over the slices.
    `hole` (0 -> 1 of `r`) cuts a donut hole in `background`; `gap` (radians)
    leaves a thin seam between slices. With `labels`, each slice's percentage
    fades in on the slice once the sweep has passed it. Returns the angle of
    the sweep's leading edge."""
    p = vb.clamp01(p)
    total = float(sum(values)) or 1.0
    edge = TOP + 2 * math.pi * p
    a = TOP
    spans = []
    for k, v in enumerate(values):
        span = 2 * math.pi * v / total
        a0, a1 = a + gap / 2, a + span - gap / 2
        if a0 < edge and a1 > a0:
            cv.sector(cx, cy, r, a0, min(a1, edge), colors[k % len(colors)])
        spans.append((a, a + span, v))
        a += span
    if hole > 0:
        demo.dot(cv, cx, cy, r * hole, color=background)
    if labels:
        f = font or demo.font(round(r * 0.12), 800)
        mid_r = r * (0.62 if hole <= 0 else (1 + hole) / 2)
        for a0, a1, v in spans:
            done = vb.clamp01((edge - a1) / 0.5 + 1) if a1 - a0 > 0 else 0  # in over the next ~0.5 rad
            if done <= 0:
                continue
            m = (a0 + a1) / 2
            demo.word(cv, f'{round(100 * v / total)}%', cx + mid_r * math.cos(m), cy + mid_r * math.sin(m),
                      font=f, color=label_color, alpha=done)
    return edge


SLICES = (38, 24, 18, 12, 8)
COLORS = (demo.ACCENT, demo.TEAL, '#f2b84b', '#6c8cf0', demo.MUTED)


def draw(n, cv):
    cx, cy, r = demo.W / 2, demo.H / 2, demo.H * 0.36
    p = vb.ease_in_out_quart(demo.phase(n, 0.3, 2.2))
    cv.arc(cx, cy, r + 12, 0, 2 * math.pi, demo.LINE, width=2)   # the empty track the sweep fills
    edge = pie_sweep(cv, cx, cy, r, SLICES, COLORS, p, hole=0.42, gap=0.03)
    if 0 < p < 1:  # the sweep's leading hand
        cv.line(cx, cy, cx + (r + 12) * math.cos(edge), cy + (r + 12) * math.sin(edge), demo.INK, width=3)
        demo.dot(cv, cx, cy, 6, color=demo.INK)
    cv.mark('pie', cx - r, cy - r, 2 * r, 2 * r)


TECHNIQUE = Technique(
    id='pie-sweep',
    name='Pie sweep',
    family='broadcast',
    group='Charts',
    aliases=('pie chart reveal', 'radial wipe pie', 'donut chart sweep', 'clock wipe chart'),
    definition='A pie or donut chart that fills in with a single clockwise sweep from the top, '
               'revealing each slice in turn as the edge passes over it.',
    phrasings=('animate the pie chart so it sweeps round like a clock hand',
               'have the donut chart draw itself in slice by slice',
               'reveal the pie segments with a circular wipe'),
    related=('circle-packing', 'circle-pop', 'cycle-diagram-rotation', 'phyllotaxis', 'highlight-circle-draw',
             'radial-repeater'),
    api=('videobuilder.techniques.broadcast.pie_sweep.pie_sweep',),
    demo=lambda: demo.film(draw),
)
