"""Axis rescale: a chart's value axis animates to a new range. The gridlines
and their labels slide along the axis as the scale stretches or squeezes,
ticks that only the old range had fade out, ticks that only the new range has
fade in, and everything plotted against the axis moves with it."""
import math

import videobuilder as vb
from videobuilder import Box, text

from .. import _demo as demo
from ..schema import Capability


def nice_ticks(lo, hi, count=5):
    """Round-numbered tick values covering `lo`..`hi`, about `count` of them
    (steps of 1, 2, 2.5 or 5 x 10^k)."""
    span = hi - lo
    if span <= 0:
        return [lo]
    raw = span / max(1, count - 1)
    k = 10 ** math.floor(math.log10(raw))
    step = next(m * k for m in (1, 2, 2.5, 5, 10) if m * k >= raw * (1 - 1e-9))
    first = math.ceil(lo / step - 1e-9)
    return [round(i * step, 10) for i in range(first, math.floor(hi / step + 1e-9) + 1)]


def rescaled_domain(frm, to, p):
    """The (lo, hi) domain `p` of the way from `frm` to `to`. The span moves
    in log space, so a 4x zoom feels as even as its first doubling."""
    lo = frm[0] + (to[0] - frm[0]) * p
    a, b = frm[1] - frm[0], to[1] - to[0]
    span = vb.log_lerp(a, b, p) if a > 0 and b > 0 else a + (b - a) * p
    return lo, lo + span


def axis_rescale(cv, plot, frm, to, p, count=5, font=None, fmt=None, ink=demo.MUTED, grid=demo.LINE,
                 ease=vb.ease_in_out_quart):
    """Draw a horizontal-gridline value axis for the Box `plot` while its
    domain moves from `frm` to `to` (each `(lo, hi)`), `p` running 0 -> 1.

    Ticks of both ranges ride the moving scale: shared ticks stay solid,
    old-only ticks fade out and new-only ticks fade in; labels sit left of
    the plot. Returns `y_of(value)`, the screen y of a value on the current
    scale, to place bars, points or lines with."""
    e = ease(vb.clamp01(p))
    lo, hi = rescaled_domain(frm, to, e)
    font = font or demo.mono(20, 600)
    fmt = fmt or (lambda v: f'{v:g}')
    lh = text.line_height(font)

    def y_of(v):
        return plot.bottom - (v - lo) / (hi - lo) * plot.h

    old, new = set(nice_ticks(*frm, count)), set(nice_ticks(*to, count))
    for v in sorted(old | new):
        alpha = 1.0 if v in old and v in new else (1 - e if v in old else e)
        y = y_of(v)
        if alpha <= 0.01 or not plot.y - 1 <= y <= plot.bottom + 1:
            continue
        base = v == 0
        cv.line(plot.x, y, plot.right, y, ink if base else grid, width=3 if base else 2, alpha=alpha)
        label = fmt(v)
        w = text.measure(label, font)
        box = text.draw(cv, [label], font, plot.x - 16 - w, y - lh / 2, ink, alpha=alpha)
        cv.mark(f'tick-{label}', *box)
    return y_of


VALUES = (34, 58, 42, 71, 50)
HERO = 360


def draw(n, cv):
    plot = Box(260, 150, demo.W - 420, demo.H - 300)
    grow = demo.phase(n, 0.3, 0.9)               # the new bar climbs to the old ceiling...
    p = demo.phase(n, 0.9, 2.3)                  # ...then the axis makes room for it
    y_of = axis_rescale(cv, plot, (0, 100), (0, 400), p)
    hero = 100 * vb.ease_out_quint(grow) + (HERO - 100) * vb.ease_in_out_quart(p)
    cols = len(VALUES) + 1
    slot = plot.w / cols
    bar = slot * 0.56
    with cv.clip(plot.x, plot.y - 4, plot.w, plot.h + 4):
        for i, v in enumerate(VALUES + (hero,)):
            if v <= 0:
                continue
            x = plot.x + slot * (i + 0.5) - bar / 2
            y = y_of(v)
            last = i == cols - 1
            cv.rect(x, y, bar, plot.bottom - y, demo.ACCENT if last else demo.TEAL, radius=8)
            cv.rect(x, plot.bottom - 8, bar, 8, demo.ACCENT if last else demo.TEAL)
            cv.mark(f'bar-{i}', x, y, bar, plot.bottom - y)
    demo.word(cv, 'Axis rescale', demo.W / 2, 82, size=44, color=demo.INK, weight=800)


CAPABILITY = Capability(
    id='axis-rescale',
    name='Axis rescale',
    family='broadcast',
    group='Charts',
    aliases=('axis zoom', 'scale change', 'dynamic axis', 'animated y-axis'),
    definition='A chart\'s value axis glides to a new range, its gridlines and labels sliding into place '
               'while the bars or lines already drawn shrink or stretch to stay true to it.',
    phrasings=('the chart zooms out so the big new bar fits',
               'animate the y-axis to the new maximum',
               'make the scale adjust smoothly when a value goes off the top'),
    related=('optical-size-shift', 'leaderboard-row-swap', 'variable-font-width-animation',
             'isolines-contour-animation', 'slant-axis-swing', 'speed-ramp'),
    api=('videobuilder.capabilities.broadcast.axis_rescale.axis_rescale',
         'videobuilder.capabilities.broadcast.axis_rescale.rescaled_domain',
         'videobuilder.capabilities.broadcast.axis_rescale.nice_ticks'),
    demo=lambda: demo.film(draw),
)
