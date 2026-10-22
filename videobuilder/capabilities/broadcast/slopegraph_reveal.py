"""Slopegraph reveal: two columns of the same items, one per moment in time,
with a straight line joining each item's two values -- the dots land on the
left axis first, then each line draws itself across to its new value, one
after another, so the eye reads every rise and fall as a slope."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def slope_positions(rows, y0, y1, lo=None, hi=None):
    """Each `(label, before, after)` row as `(label, before, after, ya, yb)`:
    both values mapped onto one shared vertical scale, `lo` at `y1` (the
    bottom) and `hi` at `y0` (the top). `lo`/`hi` default to the data's
    range, so the slopes are honest between the two columns."""
    vals = [v for _, a, b in rows for v in (a, b)]
    lo = min(vals) if lo is None else lo
    hi = max(vals) if hi is None else hi
    span = (hi - lo) or 1.0

    def y(v):
        return y1 - (v - lo) / span * (y1 - y0)
    return [(label, a, b, y(a), y(b)) for label, a, b in rows]


def draw_slopegraph(cv, rows, x0, x1, y0, y1, p, rise=demo.ACCENT, fall=demo.TEAL, ink=demo.INK,
                    muted=demo.MUTED, font=None, value_font=None, headers=None, stagger=0.55,
                    fmt=lambda v: f'{v:g}', width=3.5, lo=None, hi=None):
    """Draw a slopegraph between the axes at `x0` and `x1` (values from `y1`
    up to `y0`) at progress `p` (0 -> 1). The axes and left dots come in over
    the first fifth; then each row's line strokes from its left value to its
    right one, the rows starting `stagger` of a line's length apart (0: all
    at once, 1: strictly one after another); the right dot and its label pop
    in as the line arrives. Rising rows use `rise`, falling ones `fall`.
    `headers` labels the two columns. Returns the Box of the plot."""
    f = font or demo.font(22, 700)
    vf = value_font or demo.mono(18, 600)
    pos = slope_positions(rows, y0, y1, lo, hi)
    intro = vb.ease_out_quint(vb.clamp01(p / 0.2))
    body = vb.clamp01((p - 0.2) / 0.8)

    for x in (x0, x1):
        cv.line(x, y1 + 20, x, y1 + 20 - (y1 - y0 + 40) * intro, muted, width=2, alpha=0.7)
    if headers:
        hf = demo.font(26, 800)
        for x, h in zip((x0, x1), headers):
            demo.word(cv, h, x, y0 - 56, font=hf, color=ink, alpha=intro)

    k = len(pos)
    each = 1 / (1 + stagger * (k - 1)) if k else 1
    for i, (label, a, b, ya, yb) in enumerate(pos):
        color = rise if b >= a else fall
        demo.dot(cv, x0, ya, r=6 * intro, color=color, alpha=intro)
        va = fmt(a)
        vw, vh = vb.text.block_size([va], vf)
        shift = 30 * (1 - intro)
        vb.text.draw(cv, [va], vf, x0 - 20 - vw - shift, ya - vh / 2, muted, alpha=intro)
        tw, th = vb.text.block_size([label], f)
        vb.text.draw(cv, [label], f, x0 - 36 - vw - tw - shift, ya - th / 2, ink, alpha=intro)

        q = vb.ease_in_out_quart(vb.clamp01((body - i * stagger * each) / each))
        if q <= 0:
            continue
        cv.line(x0, ya, x0 + (x1 - x0) * q, ya + (yb - ya) * q, color, width=width)
        if q > 0.9:
            pop = vb.clamp01((q - 0.9) / 0.1)
            demo.dot(cv, x1, yb, r=6 * vb.ease_out_back(pop), color=color)
            delta = b - a
            tag = f'{fmt(b)}  {"+" if delta >= 0 else "-"}{fmt(abs(delta))}'
            tw, th = vb.text.block_size([tag], vf)
            vb.text.draw(cv, [tag], vf, x1 + 20 + 16 * (1 - pop), yb - th / 2, color, alpha=pop)
    return vb.Box(x0, y0, x1 - x0, y1 - y0)


ROWS = (('Solar', 12, 41), ('Wind', 22, 33), ('Hydro', 30, 26), ('Gas', 38, 21), ('Coal', 45, 9))


def draw(n, cv):
    box = draw_slopegraph(cv, ROWS, demo.W * 0.36, demo.W * 0.64, demo.H * 0.25, demo.H * 0.85, demo.phase(n, 0.2, 2.6),
                          headers=('2015', '2025'), fmt=lambda v: f'{v:g}%', stagger=0.45)
    cv.mark('chart', *box)


CAPABILITY = Capability(
    id='slopegraph-reveal',
    name='Slopegraph reveal',
    family='broadcast',
    group='Charts',
    aliases=('slope chart', 'slope graph', 'before-and-after line chart'),
    definition='Items listed down two facing columns, one per point in time, are joined by straight lines '
               'that draw across one by one, so each rise or drop shows as a slope.',
    phrasings=('animate a before and after comparison with lines connecting the two years',
               'draw lines from the old values to the new ones so we can see who went up and who went down',
               'a two-column chart where each item gets a sloped line between then and now'),
    related=('streamlines', 'dimension-line-annotation', 'speed-lines', 'org-chart-grow', 'wireframe-terrain',
             'staggered-cascade-reveal'),
    api=('videobuilder.capabilities.broadcast.slopegraph_reveal.draw_slopegraph',
         'videobuilder.capabilities.broadcast.slopegraph_reveal.slope_positions'),
    demo=lambda: demo.film(draw),
)
