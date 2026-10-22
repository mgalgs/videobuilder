"""Series isolate highlight: a multi-line chart picks out one series -- every
other line sinks to a faint grey while the chosen one stays in colour,
thickens and gains its point markers, and its legend chip lights up. Moving
the focus to another series hands the emphasis across."""
import videobuilder as vb
from videobuilder import Box, paths

from .. import _demo as demo
from ..schema import Technique


def _mix(a, b, t):
    """Colour `a` -> `b` at `t` (0..1), as a 0-255 (r, g, b) tuple."""
    ra, rb = vb.canvas.rgba(a), vb.canvas.rgba(b)
    return tuple(round(255 * (x + (y - x) * t)) for x, y in zip(ra[:3], rb[:3]))


def isolate_weights(count, focus, p, previous=None):
    """Per-series emphasis (0..1) for `count` series while the focus moves
    from `previous` (an index, or None for "no focus yet") to `focus` at
    progress `p`. Feed the result to `series_isolate_highlight`."""
    p = vb.clamp01(p)
    return tuple((p if i == focus else 0.0) + ((1 - p) if i == previous else 0.0) for i in range(count))


def series_isolate_highlight(cv, box, series, weights, amount=1.0, lo=0.0, hi=100.0, dim='#5b5f69',
                             categories=None, width=3.0, bold=6.0):
    """Draw a multi-line chart in `box` with some series isolated.

    `series`: a sequence of (label, colour, values); `weights`: one emphasis
    per series, 0..1 (see `isolate_weights`); `amount`: 0 draws every line in
    its own colour, 1 fully isolates -- unweighted lines fade to `dim`, the
    weighted ones keep their colour, grow to `bold` px and show their points.
    `lo`/`hi` is the value range; `categories` labels the x axis. A legend of
    chips runs across the top of `box`, the emphasised chip lit up."""
    amount = vb.clamp01(amount)
    legend_h = 64
    axis_f, chip_f = demo.mono(18, 500), demo.font(20, 700)
    plot = Box(box.x + 56, box.y + legend_h + 30, box.w - 72, box.h - legend_h - 30 - 44)
    n = max(len(v) for _, _, v in series)

    # grid and axis labels
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        y = plot.bottom - plot.h * k / 4
        cv.line(plot.x, y, plot.right, y, demo.LINE, width=2)
        vb.text.draw(cv, [f'{v:g}'], axis_f, box.x, y - 12, demo.MUTED)
    for i, c in enumerate(categories or ()):
        x = plot.x + plot.w * i / max(1, n - 1)
        demo.word(cv, c, x, plot.bottom + 28, font=axis_f, color=demo.MUTED)

    # legend chips
    chip_w = min(240, box.w / len(series))
    for i, (label, color, _) in enumerate(series):
        e = weights[i] * amount
        x = box.x + i * chip_w
        if e > 0.01:
            cv.rect(x, box.y, chip_w - 16, legend_h - 8, '#262931', radius=10, alpha=e)
            cv.rect(x + 14, box.y + legend_h - 18, (chip_w - 44) * e, 4, color, radius=2, alpha=e)
        fade = amount * (1 - weights[i])
        cv.line(x + 22, box.y + 28, x + 54, box.y + 28, _mix(color, dim, fade), width=4)
        vb.text.draw(cv, [label], chip_f, x + 66, box.y + 15, _mix(demo.INK, demo.MUTED, fade))

    # lines: the least emphasised first, so the focus draws on top
    def pts(values):
        return [(plot.x + plot.w * i / max(1, n - 1), plot.bottom - plot.h * (v - lo) / (hi - lo))
                for i, v in enumerate(values)]
    for i in sorted(range(len(series)), key=lambda i: weights[i]):
        _, color, values = series[i]
        w = weights[i] * amount
        fade = amount * (1 - weights[i])
        line = pts(values)
        paths.draw(cv, line, _mix(color, dim, fade), width=width + (bold - width) * w, alpha=1 - 0.45 * fade)
        for x, y in line:
            demo.dot(cv, x, y, r=3 + 4 * w, color=_mix(color, dim, fade), alpha=max(0.35 * (1 - fade), w))


SERIES = (('Current', '#f2b134', (42, 68, 55, 87, 61, 74, 49, 80)),
          ('Previous', '#8f86ff', (68, 55, 87, 61, 74, 49, 80, 42)),
          ('Baseline', '#d9dce3', (55, 87, 61, 74, 49, 80, 42, 68)))
CATEGORIES = tuple('ABCDEFGH')


def draw(n, cv):
    t = n / demo.FPS
    amount = vb.ease_in_out_quart(demo.phase(n, 0.5, 1.0))
    if t < 1.7:
        weights = isolate_weights(3, 0, 1)
    else:
        weights = isolate_weights(3, 1, vb.ease_in_out_quart(demo.phase(n, 1.7, 2.2)), previous=0)
    box = Box(220, 90, demo.W - 440, demo.H - 170)
    series_isolate_highlight(cv, box, SERIES, weights, amount, categories=CATEGORIES)
    cv.mark('chart', box.x, box.y, box.w, box.h)


TECHNIQUE = Technique(
    id='series-isolate-highlight',
    name='Series isolate highlight',
    family='broadcast',
    group='Charts',
    aliases=('legend highlight', 'focus series', 'series focus'),
    definition='In a chart with several lines, the other lines drain to a faint grey so that one chosen '
               'line is left standing out in bold colour.',
    phrasings=('grey out every line except the one I want to talk about',
               'make one series pop and fade the rest of the chart back',
               'highlight a single line on the graph when its legend entry is picked'),
    related=('difference-highlight', 'callout-highlight', 'shine-glint-sweep', 'luma-wipe', 'spotlight-hover',
             'highlighter-swipe'),
    api=('videobuilder.techniques.broadcast.series_isolate_highlight.series_isolate_highlight',
         'videobuilder.techniques.broadcast.series_isolate_highlight.isolate_weights'),
    demo=lambda: demo.film(draw),
)
