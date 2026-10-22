"""Bar grow: the bars of a chart rise out of a shared baseline to their
values, one after another from left to right. (The compendium's `bar-chart`
component is a whole titled shot; this is the move on its own, for any box.)"""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def bar_grow(count, p, stagger=0.6, ease=vb.ease_out_quint):
    """Each of `count` bars' grown fraction (0 -> 1) at overall progress `p`.
    Bar `i` starts at `i / (count - 1) * stagger` of the way through and every
    bar takes the same time, so the last finishes at `p = 1`. `stagger=0`
    grows them all together."""
    span = 1 - stagger if count > 1 else 1
    out = []
    for i in range(count):
        start = stagger * i / (count - 1) if count > 1 else 0
        out.append(ease(vb.clamp01((p - start) / span)) if span > 0 else float(p >= start))
    return out


def draw_bar_grow(cv, box, values, p, top=None, color=demo.TEAL, hero=None, hero_color=demo.ACCENT,
                  gap=0.4, radius=6, stagger=0.6, labels=None, font=None, label_color=demo.MUTED):
    """Draw `values` as bars standing on the bottom of `box`, grown to
    progress `p`. `top` is the value that fills the box's height (default the
    largest value). Bar `hero` (an index) is drawn in `hero_color`. `gap` is
    the space between bars as a fraction of a column. With `labels` and a
    `font`, each value's label appears above its bar once the bar is up.
    Returns each bar's drawn height."""
    top = top or max(values)
    col = box.w / len(values)
    bw = col * (1 - gap)
    heights = []
    for i, (v, g) in enumerate(zip(values, bar_grow(len(values), p, stagger))):
        h = box.h * max(0.0, v) / top * g
        x = box.x + col * i + (col - bw) / 2
        if h > 0.5:
            cv.rect(x, box.bottom - h, bw, h, hero_color if i == hero else color, radius=min(radius, h / 2))
            cv.mark(f'bar-{i}', x, box.bottom - h, bw, h)
        if labels and font and g > 0.85:
            lw, lh = vb.text.block_size([labels[i]], font)
            vb.text.draw(cv, [labels[i]], font, x + (bw - lw) / 2, box.bottom - h - lh - 8,
                         hero_color if i == hero else label_color, alpha=vb.clamp01((g - 0.85) / 0.15))
        heights.append(h)
    return heights


VALUES = (42, 68, 55, 87, 61, 74, 47, 79)


def draw(n, cv):
    box = vb.Box(150, 110, demo.W - 300, demo.H - 210)
    for k in range(1, 5):  # gridlines at quarters
        y = box.bottom - box.h * k / 4
        cv.line(box.x, y, box.right, y, demo.LINE, width=1)
    draw_bar_grow(cv, box, VALUES, demo.phase(n, 0.3, 2.3), top=100, hero=3,
                  labels=[str(v) for v in VALUES], font=demo.mono(20, 700))
    cv.line(box.x - 10, box.bottom, box.right + 10, box.bottom, demo.MUTED, width=3)
    f = demo.font(18, 600)
    col = box.w / len(VALUES)
    for i in range(len(VALUES)):
        lbl = 'ABCDEFGH'[i]
        lw, _ = vb.text.block_size([lbl], f)
        vb.text.draw(cv, [lbl], f, box.x + col * (i + 0.5) - lw / 2, box.bottom + 14, demo.MUTED)


TECHNIQUE = Technique(
    id='bar-grow',
    name='Bar grow',
    family='broadcast',
    group='Charts',
    aliases=('bar chart build', 'column grow', 'growing bars'),
    definition='The bars of a chart shoot up from a common baseline to their values, '
               'each starting a beat after the one to its left.',
    phrasings=('make the bar chart animate up from zero',
               'have the columns rise one by one to their numbers',
               'grow the bars in from the bottom'),
    related=('isometric-bar-rise', 'org-chart-grow', 'decision-tree-branch-growth', 'audio-waveform-bars',
             'shape-stacking-drop', 'percentage-fill-bar'),
    api=('videobuilder.techniques.broadcast.bar_grow.draw_bar_grow',
         'videobuilder.techniques.broadcast.bar_grow.bar_grow'),
    demo=lambda: demo.film(draw),
)
