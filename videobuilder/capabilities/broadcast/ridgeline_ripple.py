"""Ridgeline ripple: a stack of density curves, one per row, each sitting a
little below the last so the peaks overlap the rows above. The rows swell up
from flat baselines one after another, top to bottom, so the reveal runs
down the chart like a ripple."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ...canvas import rgba


def density(bumps, samples=80):
    """A smooth curve of `samples` heights in [0, 1] made of Gaussian bumps.
    `bumps` is a sequence of `(centre, width, weight)`, centre and width as
    fractions of the x range; the tallest point is scaled to 1."""
    ys = []
    for s in range(samples):
        x = s / (samples - 1)
        ys.append(sum(wt * math.exp(-((x - c) / w) ** 2 / 2) for c, w, wt in bumps))
    top = max(ys) or 1.0
    return [y / top for y in ys]


def ridgeline_ripple(cv, curves, progress, x, y, w, h, peak=None, stagger=0.55, ease=vb.ease_out_back,
                     fill=demo.TEAL, stroke=demo.INK, fill_alpha=0.85, highlight=None, highlight_color=demo.ACCENT,
                     width=2.5):
    """Draw `curves` (each a list of heights in [0, 1]) as a ridgeline chart in
    the box (x, y, w, h), one baseline per row from top to bottom.

    `progress` runs 0 -> 1 over the whole reveal; each row's own rise starts
    `stagger` of a row's span after the one above, so the rows ripple in
    down the stack, growing from a flat line to full height along `ease`.
    `peak` is a full-height curve's rise in px (default: two row gaps, so
    ridges overlap the rows above). Lower rows are drawn last and cover the
    ones behind them. `highlight` is the index of a row stroked in
    `highlight_color`. Returns the baseline y of every row."""
    rows = len(curves)
    gap = h / max(1, rows)
    peak = 2.0 * gap if peak is None else peak
    span = 1.0 / (1 + stagger * (rows - 1))   # each row's share of `progress`
    ctx = cv.ctx
    r, g, b, _ = rgba(fill)
    bases = []
    for k, ys in enumerate(curves):
        base = y + gap * (k + 1)
        bases.append(base)
        q = vb.clamp01((progress - k * stagger * span) / span)
        if q <= 0:
            continue
        lift = peak * ease(q)
        n = len(ys)
        pts = [(x + w * i / (n - 1), base - lift * v) for i, v in enumerate(ys)]
        ctx.move_to(x, base)
        for px, py in pts:
            ctx.line_to(px, py)
        ctx.line_to(x + w, base)
        ctx.close_path()
        ctx.set_source_rgba(r, g, b, fill_alpha * min(1.0, q * 3))
        ctx.fill()
        ctx.move_to(*pts[0])
        for px, py in pts[1:]:
            ctx.line_to(px, py)
        sr, sg, sb, _ = rgba(highlight_color if k == highlight else stroke)
        ctx.set_source_rgba(sr, sg, sb, min(1.0, q * 4))
        ctx.set_line_width(width)
        ctx.stroke()
    return bases


ROWS = 'ABCDEFGH'
CURVES = [density(bumps) for bumps in (
    ((0.30, 0.10, 1.0), (0.50, 0.08, 0.6)),
    ((0.55, 0.11, 1.0), (0.20, 0.05, 0.25)),
    ((0.40, 0.10, 1.0),),
    ((0.62, 0.10, 1.0), (0.20, 0.04, 0.2)),
    ((0.45, 0.12, 1.0), (0.70, 0.06, 0.4)),
    ((0.50, 0.09, 1.0), (0.25, 0.05, 0.35)),
    ((0.35, 0.12, 1.0),),
    ((0.55, 0.09, 1.0), (0.25, 0.06, 0.3)),
)]


def draw(n, cv):
    x, y, w, h = 130, 80, demo.W - 250, demo.H - 160
    p = demo.phase(n, 0.2, 2.5)
    bases = ridgeline_ripple(cv, CURVES, p, x, y, w, h, fill='#3b4f8f', stroke='#c9d3ff',
                             highlight=len(CURVES) - 1, highlight_color='#f2c14e')
    f = demo.font(22, 800)
    for k, base in enumerate(bases):
        vb.text.draw(cv, [ROWS[k]], f, x - 44, base - 14, demo.INK)
    axis = demo.mono(15)
    for i, tick in enumerate(('0', '25', '50', '75', '100')):
        tw, _ = vb.text.block_size([tick], axis)
        vb.text.draw(cv, [tick], axis, x + w * i / 4 - tw / 2, bases[-1] + 16, demo.MUTED)
    cv.mark('chart', x, y, w, h)


CAPABILITY = Capability(
    id='ridgeline-ripple',
    name='Ridgeline ripple',
    family='broadcast',
    group='Charts',
    aliases=('joy plot reveal', 'stacked density ridges', 'ridgeline plot', 'joyplot'),
    definition='A chart of distribution curves stacked in rows, each peak overlapping the row above, that '
               'swell up from flat lines one row after another so the reveal rolls down the stack.',
    phrasings=('show the distributions as overlapping ridges that grow in row by row',
               'a joy plot where each curve rises up after the one above it',
               'stack the density curves like mountain ridges and animate them in from the top'),
    related=('ripple', 'ripple-rings', 'refraction-ripple', 'ripple-displacement', 'location-ripple-pulse',
             'height-field-ripples'),
    api=('videobuilder.capabilities.broadcast.ridgeline_ripple.ridgeline_ripple',
         'videobuilder.capabilities.broadcast.ridgeline_ripple.density'),
    demo=lambda: demo.film(draw),
)
