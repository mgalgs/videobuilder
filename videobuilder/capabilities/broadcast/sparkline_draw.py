"""Sparkline Draw: a tiny, axis-free line chart traces itself left to right
beside a headline figure, a dot riding its tip, so the number arrives with
its trend."""
import videobuilder as vb
from videobuilder import paths

from .. import _demo as demo
from ..schema import Capability


def sparkline_points(values, x, y, w, h, pad=0.08):
    """`values` as a point list filling the box (x, y, w, h): evenly spaced
    left to right, the lowest value at the bottom and the highest at the top,
    `pad` (a fraction of `h`) kept clear above and below. A flat series sits
    on the middle line."""
    lo, hi = min(values), max(values)
    span = hi - lo
    last = max(len(values) - 1, 1)
    inner = h * (1 - 2 * pad)
    return [(x + w * i / last,
             y + h / 2 if span == 0 else y + h * pad + inner * (1 - (v - lo) / span))
            for i, v in enumerate(values)]


def draw_sparkline(cv, values, x, y, w, h, progress, color=demo.TEAL, width=4, fill=0.16,
                   tip=demo.INK, tip_r=7, pad=0.08):
    """Draw the sparkline of `values` in the box (x, y, w, h) grown to
    `progress` (0 -> 1 along its length): the line in `color`, a soft wash of
    the same colour beneath it down to the box's bottom (`fill` is its alpha,
    0 for none) and a dot of `tip` colour on the leading point (`tip=None` for
    none). Returns the tip's (x, y), or None before the line starts."""
    pts = sparkline_points(values, x, y, w, h, pad)
    done = paths.reveal(pts, vb.clamp01(progress))
    if len(done) < 2:
        return None
    if fill > 0:
        paths.draw(cv, done + [(done[-1][0], y + h), (done[0][0], y + h)], color, fill=True, alpha=fill)
    paths.draw(cv, done, color, width=width)
    end = done[-1]
    if tip:
        demo.dot(cv, end[0], end[1], tip_r * 2.2, color=tip, alpha=0.2)
        demo.dot(cv, end[0], end[1], tip_r, color=tip)
    return end


SERIES = (41, 44, 39, 47, 52, 49, 55, 51, 58, 63, 60, 68, 66, 74, 71, 80)


def draw(n, cv):
    p = vb.ease_in_out_quart(demo.phase(n, 0.35, 2.35))
    # the figure ticks up with the line, reading the value under its tip
    i = p * (len(SERIES) - 1)
    k = min(int(i), len(SERIES) - 2)
    value = SERIES[k] + (SERIES[k + 1] - SERIES[k]) * (i - k)
    left, top = 180, demo.H / 2 - 70
    vb.text.draw(cv, ['WEEKLY SIGNUPS'], demo.font(18, 700), left + 4, top, demo.MUTED)
    box = vb.text.draw(cv, [f'{value:.0f}k'], demo.font(96, 800), left, top + 22, demo.INK)
    cv.mark('figure', *box)
    bx, by, bw, bh = 420, top + 30, 360, 110
    up = demo.phase(n, 2.3, 2.7)
    if up > 0:
        vb.text.draw(cv, ['+95%'], demo.font(22, 700), bx + bw + 14, by - 6 + 6 * (1 - up), demo.TEAL,
                     alpha=up)
    draw_sparkline(cv, SERIES, bx, by, bw, bh, p, width=3, tip_r=5)
    cv.mark('sparkline', bx, by, bw, bh)


CAPABILITY = Capability(
    id='sparkline-draw',
    name='Sparkline draw',
    family='broadcast',
    group='Charts',
    aliases=('spark line reveal', 'inline trend line', 'sparkline animation'),
    definition='A small line chart with no axes traces itself from left to right next to a key figure, '
               'showing at a glance which way the number has been heading.',
    phrasings=('a little trend line draws in next to the stat',
               'animate a mini line graph beside the number',
               'show the figure with a tiny chart sketching its history'),
    related=('streamlines', 'stroke-draw-on', 'magnetic-field-lines', 'line-weave', 'map-route-draw',
             'isolines-contour-animation'),
    api=('videobuilder.capabilities.broadcast.sparkline_draw.draw_sparkline',
         'videobuilder.capabilities.broadcast.sparkline_draw.sparkline_points',
         'videobuilder.paths.reveal'),
    demo=lambda: demo.film(draw),
)
