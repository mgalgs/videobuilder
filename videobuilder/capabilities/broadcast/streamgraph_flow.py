"""Streamgraph flow: a stacked area chart whose layers are piled around a
wandering centre line instead of a flat axis, so the series read as soft
coloured ribbons that swell, thin and drift sideways like a river."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def streamgraph_layers(series, baseline='wiggle'):
    """Stack `series` (k layers, each a list of n non-negative values) into
    streamgraph bands. Returns k lists of (lo, hi) pairs, in value units, with
    the whole stack centred on 0. `baseline` is 'wiggle' (the centre line
    wanders to keep each band's slope small -- the classic streamgraph) or
    'silhouette' (the stack is mirrored about a straight centre)."""
    k, n = len(series), len(series[0])
    totals = [sum(s[j] for s in series) for j in range(n)]
    if baseline == 'silhouette':
        base = [-t / 2 for t in totals]
    elif baseline == 'wiggle':
        base, y = [0.0], 0.0
        for j in range(1, n):
            s1 = s2 = 0.0
            for i in range(k):
                now, was = series[i][j], series[i][j - 1]
                below = sum(series[m][j] - series[m][j - 1] for m in range(i))
                s1 += now
                s2 += ((now - was) / 2 + below) * now
            y -= s2 / s1 if s1 else 0.0
            base.append(y)
        mid = sum(b + t / 2 for b, t in zip(base, totals)) / n
        base = [b - mid for b in base]
    else:
        raise ValueError(f'unknown streamgraph baseline {baseline!r}')
    out, lo = [], base
    for s in series:
        hi = [a + v for a, v in zip(lo, s)]
        out.append(list(zip(lo, hi)))
        lo = hi
    return out


def _smooth(ctx, pts, start):
    """Trace `pts` as a Catmull-Rom curve (as cubic Béziers), moving to the
    first point when `start`, else joining it with a line."""
    (ctx.move_to if start else ctx.line_to)(*pts[0])
    for i in range(len(pts) - 1):
        p0, p1, p2 = pts[max(i - 1, 0)], pts[i], pts[i + 1]
        p3 = pts[min(i + 2, len(pts) - 1)]
        ctx.curve_to(p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6,
                     p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6, *p2)


def streamgraph(cv, series, box, colors, baseline='wiggle', scale=None, reveal=1.0, alpha=1.0):
    """Draw `series` as a streamgraph filling `box` (x, y, w, h): one smooth
    band per series, coloured from `colors` in turn, stacked about the box's
    middle. `scale` is px per value unit (default: fit the tallest stack, so
    pass a fixed one to keep the height steady while data streams through).
    `reveal` in [0, 1] wipes the chart in from the left. Returns the bands as
    lists of (x, y_top, y_bottom) in px, for labels."""
    x, y, w, h = box
    bands = streamgraph_layers(series, baseline)
    n = len(series[0])
    if scale is None:
        span = max(max(-bands[0][j][0], bands[-1][j][1]) for j in range(n)) or 1.0
        scale = h / 2 / span
    xs = [x + w * j / (n - 1) for j in range(n)]
    mid = y + h / 2
    px = []
    ctx = cv.ctx
    ctx.save()
    ctx.rectangle(x, y - h, w * vb.clamp01(reveal), h * 3)
    ctx.clip()
    for i, band in enumerate(bands):
        top = [(xs[j], mid - band[j][1] * scale) for j in range(n)]
        bot = [(xs[j], mid - band[j][0] * scale) for j in range(n)]
        _smooth(ctx, top, True)
        _smooth(ctx, bot[::-1], False)
        ctx.close_path()
        ctx.set_source_rgba(*vb.rgba(colors[i % len(colors)], alpha))
        ctx.fill()
        px.append([(xs[j], top[j][1], bot[j][1]) for j in range(n)])
    ctx.restore()
    return px


PALETTE = ('#ef5b4c', '#f08a4b', '#f2c14e', '#4fc3b0', '#3b8ea5', '#6c5b9e')
NAMES = ('Rock', 'Pop', 'Folk', 'Jazz', 'Soul', 'Rap')


def _value(i, t):
    """Series `i` at time `t`: a smooth, always-positive rise and fall."""
    return (0.06 + 1.5 * max(0.0, math.sin(0.6 * t + 1.9 * i)) ** 3
            + 0.35 * math.sin(1.4 * t + 2.9 * i) ** 2)


def draw(n, cv):
    t = n / demo.FPS
    samples, window = 40, 9.0
    drift = 1.6 * t  # the data scrolls left: new values flow in at the right
    series = [[_value(i, drift + window * j / (samples - 1)) for j in range(samples)]
              for i in range(len(PALETTE))]
    box = (0, 40, demo.W, demo.H - 80)
    reveal = 1 - (1 - demo.phase(n, 0.1, 1.1)) ** 3
    bands = streamgraph(cv, series, box, PALETTE, scale=62, reveal=reveal)
    f = demo.font(15, 700)
    a = demo.phase(n, 1.0, 1.5)
    for i, band in enumerate(bands):
        j = max(range(len(band) // 3, len(band) * 2 // 3), key=lambda j: band[j][2] - band[j][1])
        bx, top, bot = band[j]
        if bot - top > 34:
            demo.word(cv, NAMES[i], bx, (top + bot) / 2, font=f, color=demo.BG, alpha=a * 0.85)
    cv.mark('stream', *box)


CAPABILITY = Capability(
    id='streamgraph-flow',
    name='Streamgraph flow',
    family='broadcast',
    group='Charts',
    aliases=('streamgraph', 'theme river', 'stream graph', 'flowing stacked area chart'),
    definition='Several data series stacked as smooth coloured ribbons around a wavy centre line, '
               'swelling and thinning over time so the whole chart looks like a flowing river.',
    phrasings=('a stacked area chart that flows like a river around the middle',
               'show how the share of each category changes over time as wavy coloured streams',
               'animated organic ribbons of data drifting across the screen'),
    related=('streamlines', 'flow-map-lines', 'curl-noise-flow', 'flowchart-build', 'flow-field', 'line-boil'),
    api=('videobuilder.capabilities.broadcast.streamgraph_flow.streamgraph',
         'videobuilder.capabilities.broadcast.streamgraph_flow.streamgraph_layers'),
    demo=lambda: demo.film(draw),
)
