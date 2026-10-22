"""Stacked bar build: a chart column fills from its baseline one segment at a
time, each new segment growing up on top of the ones already in place, so the
column's height climbs to the total."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def stacked_bar_build(cv, x, base_y, width, segments, scale, p, overlap=0.0, ease=vb.ease_out_quint,
                      gap=2.0, on_segment=None):
    """Draw one stacked column whose bottom-left corner sits at (`x`, `base_y`)
    at progress `p` (0 -> 1). `segments` are (value, color) pairs from the
    base up; a value of `v` stands `v * scale` pixels tall. Each segment grows
    over an equal slice of the run, starting when the one below is
    `1 - overlap` of the way grown (`overlap` 0: strictly one after another).
    `gap` pixels of background separate the segments. `on_segment(cv, i, box,
    q)`, if given, runs after segment `i` is painted with its current
    `vb.Box` and its own progress. Returns (running total, top y) -- the
    summed shown value and the y of the column's current top."""
    n = len(segments)
    step = 1 / (n - (n - 1) * overlap) if n else 1.0
    top, total = float(base_y), 0.0
    for i, (value, color) in enumerate(segments):
        q = vb.clamp01((p - i * step * (1 - overlap)) / step)
        if q <= 0:
            break
        shown = value * ease(q)
        h = shown * scale
        total += shown
        box = vb.Box(x, top - h, width, h)
        if h > gap:
            cv.rect(box.x, box.y + gap, box.w, box.h - gap, color)
        if on_segment:
            on_segment(cv, i, box, q)
        top -= h
    return total, top


SERIES = (('Web', demo.ACCENT), ('Retail', demo.TEAL), ('Wholesale', '#f2b84b'), ('Other', '#8a7ff0'))
COLUMNS = (('Q1', (38, 22, 18, 10)), ('Q2', (46, 30, 20, 12)), ('Q3', (52, 34, 31, 15)), ('Q4', (68, 40, 36, 18)))
SCALE, BAR_W = 1.6, 74


def draw(n, cv):
    base = demo.H - 80
    left, right = 230, demo.W - 200
    tick_f, label_f = demo.mono(13, 500), demo.font(15, 700)
    for v in range(0, 201, 50):
        y = base - v * SCALE
        cv.line(left, y, right, y, demo.LINE if v else demo.MUTED, width=1 if v else 2)
        vb.text.draw(cv, [str(v)], tick_f, left - 46, y - 8, demo.MUTED, align='right', width=36)
    pitch = (right - left) / len(COLUMNS)
    for c, (name, values) in enumerate(COLUMNS):
        x = left + pitch * (c + 0.5) - BAR_W / 2
        p = demo.phase(n, 0.25 + 0.18 * c, 1.75 + 0.18 * c)
        segs = [(v, color) for v, (_, color) in zip(values, SERIES)]
        total, top = stacked_bar_build(cv, x, base, BAR_W, segs, SCALE, p, overlap=0.15)
        demo.word(cv, name, x + BAR_W / 2, base + 22, size=15, color=demo.MUTED, weight=700)
        if p > 0:
            demo.word(cv, str(round(total)), x + BAR_W / 2, top - 16, size=19, weight=800)
        cv.mark(f'bar-{c}', x, top, BAR_W, base - top)
    lx = left
    for name, color in SERIES:
        cv.rect(lx, 44, 14, 14, color, radius=3)
        box = vb.text.draw(cv, [name], label_f, lx + 22, 41, demo.INK)
        lx = box.right + 28


TECHNIQUE = Technique(
    id='stacked-bar-build',
    name='Stacked bar build',
    family='broadcast',
    group='Charts',
    aliases=('stacked column grow', 'segmented bar build'),
    definition='A chart column builds up from its baseline in coloured pieces, each new piece rising on top '
               'of the last until the bar reaches its full total.',
    phrasings=('make the stacked bars grow one colour at a time',
               'build each column up piece by piece so you can see what adds up to the total',
               'animate a stacked column chart filling from the bottom'),
    related=('shape-stacking-drop', 'stacked-line-build', 'pyramid-build', 'isometric-bar-rise', 'org-chart-grow',
             'voxel-build'),
    api=('videobuilder.techniques.broadcast.stacked_bar_build.stacked_bar_build',),
    demo=lambda: demo.film(draw),
)
