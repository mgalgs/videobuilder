"""Polar area rose: a round chart cut into equal-angle wedges, one per
category, each pushing out from the centre until its area stands for its
value, so a bigger number reads as a bigger petal."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def polar_area_rose(values, p, radius, stagger=0.5, start=-math.pi / 2):
    """Wedges of a polar area rose at growth progress `p` (0 -> 1) as
    `(a0, a1, r)` tuples, one per value, clockwise from angle `start` (top).
    Every wedge spans the same angle; its final radius is
    `radius * sqrt(value / max)`, so its area, not its radius, is in
    proportion to its value. Wedges start one after another across the first
    `stagger` of the growth and each swells out with a small overshoot."""
    p = vb.clamp01(p)
    top = max(values) or 1
    step = 2 * math.pi / len(values)
    out = []
    for i, v in enumerate(values):
        at = stagger * i / max(len(values) - 1, 1)
        q = vb.clamp01((p - at) / (1 - stagger)) if stagger < 1 else float(p >= at)
        r = radius * math.sqrt(max(v, 0) / top) * vb.ease_out_back(q)
        out.append((start + i * step, start + (i + 1) * step, max(r, 0.0)))
    return out


def draw_polar_area_rose(cv, cx, cy, values, p, radius=150, colors=(demo.ACCENT, demo.TEAL), labels=None,
                         rings=3, gap=demo.BG, label_alpha=1.0, **kw):
    """Draw a polar area rose of `values` centred at (cx, cy) at progress `p`:
    faint guide rings, the wedges (coloured by cycling `colors`, split by thin
    `gap`-coloured spokes), and, if given, `labels` set just outside each
    wedge's final rim with its value beneath, at `label_alpha`. `kw` goes to
    `polar_area_rose`."""
    for k in range(1, rings + 1):
        cv.arc(cx, cy, radius * k / rings, 0, 2 * math.pi, demo.LINE, width=1.5)
    wedges = polar_area_rose(values, p, radius, **kw)
    for i, (a0, a1, r) in enumerate(wedges):
        if r > 0:
            cv.sector(cx, cy, r, a0, a1, colors[i % len(colors)], alpha=0.95)
    for a0, a1, r in wedges:
        if r > 0:
            cv.line(cx, cy, cx + r * math.cos(a0), cy + r * math.sin(a0), gap, width=2)
            cv.line(cx, cy, cx + r * math.cos(a1), cy + r * math.sin(a1), gap, width=2)
    if labels and label_alpha > 0:
        final = polar_area_rose(values, 1, radius, **kw)
        for (a0, a1, r), name, v in zip(final, labels, values):
            mid, d = (a0 + a1) / 2, r + 30
            x, y = cx + d * math.cos(mid), cy + d * math.sin(mid)
            demo.word(cv, name, x, y - 8, size=17, weight=800, alpha=label_alpha)
            demo.word(cv, str(v), x, y + 10, size=14, color=demo.MUTED, weight=600, alpha=label_alpha)


VALUES = (42, 68, 55, 87, 61, 74, 30, 50)
LABELS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug')
COLORS = (demo.ACCENT, '#f28b6a', demo.TEAL, '#8fd9cb', '#f5c45e', '#7c8cf0', '#b58cf0', '#e98ab8')


def draw(n, cv):
    cx, cy = demo.W / 2, demo.H / 2
    p = demo.phase(n, 0.2, 2.2)
    draw_polar_area_rose(cv, cx, cy, VALUES, p, radius=175, colors=COLORS, labels=LABELS,
                         label_alpha=demo.phase(n, 1.9, 2.5))
    cv.mark('rose', cx - 175, cy - 175, 350, 350)


TECHNIQUE = Technique(
    id='polar-area-rose',
    name='Polar area rose',
    family='broadcast',
    group='Charts',
    aliases=('Nightingale rose', 'coxcomb chart', 'polar area chart', 'rose chart'),
    definition='A circle split into equal slices that each swell outward from the middle by a different '
               'amount, so the size of every slice shows how big its number is.',
    phrasings=('a pie chart where the slices stick out by different lengths instead of different widths',
               'animate a flower-shaped chart with petals growing out from the centre for each value',
               'a radial bar chart made of wedges that grow outward'),
    related=('spiral-bloom', 'phyllotaxis', 'sound-reactive-radial-shape', 'polar-coordinate-warp',
             'hub-and-spoke-spread', 'card-deck-fan'),
    api=('videobuilder.techniques.broadcast.polar_area_rose.draw_polar_area_rose',
         'videobuilder.techniques.broadcast.polar_area_rose.polar_area_rose'),
    demo=lambda: demo.film(draw),
)
