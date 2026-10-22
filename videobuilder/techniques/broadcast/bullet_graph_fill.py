"""Bullet graph fill: a compact horizontal gauge. Shaded bands mark the
poor / fair / good ranges, a thin bar grows to the actual value, and an
upright tick marks the target, so the reader sees at a glance whether the
bar stops short of the line or runs past it."""
import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ..schema import Technique

BANDS = ((0.5, '#24262e'), (0.75, '#30333d'), (1.0, '#3d4150'))


def bullet_graph(cv, x, y, w, h, value, target, p=1.0, maximum=100.0, bands=BANDS,
                 color=demo.ACCENT, marker=demo.INK, bar=0.36, ease=vb.ease_out_expo):
    """One bullet graph in the box (x, y, w, h). `bands` are (upper bound as
    a fraction of `maximum`, colour) pairs, drawn darkest-first behind; the
    value bar, `bar` of the box's height, fills from the left to `value` as
    `p` runs 0 -> 1 (eased by `ease`); a tick at `target` spans the box.
    Returns the value shown at this point of the fill, for a counter."""
    lo = 0.0
    for hi, c in bands:
        cv.rect(x + w * lo, y, w * (hi - lo), h, c)
        lo = hi
    shown = value * ease(vb.clamp01(p))
    bh = h * bar
    fw = w * min(1.0, max(0.0, shown / maximum))
    if fw > 0.5:
        cv.rect(x, y + (h - bh) / 2, fw, bh, color)
    tx = x + w * min(1.0, target / maximum)
    cv.line(tx, y - h * 0.18, tx, y + h * 1.18, marker, width=max(2.0, h * 0.1))
    return shown


ROWS = (('North', 82, 70), ('South', 54, 70), ('East', 71, 65), ('West', 38, 60))


def draw(n, cv):
    x, w, h, gap = 230, 560, 44, 34
    top = (demo.H - len(ROWS) * h - (len(ROWS) - 1) * gap) / 2 + 10
    label_f, value_f, small_f = demo.font(26, 700), demo.mono(28, 700), demo.font(16, 600)
    intro = demo.phase(n, 0.0, 0.5)
    vb.text.draw(cv, ['vs. target'], small_f, x, top - 56, demo.MUTED, alpha=intro)
    for i, (name, value, target) in enumerate(ROWS):
        y = top + i * (h + gap)
        with cv.layer(opacity=demo.phase(n, 0.05 * i, 0.4 + 0.05 * i)):
            lw, lh = vb.text.block_size([name], label_f)
            vb.text.draw(cv, [name], label_f, x - 30 - lw, y + (h - lh) / 2, demo.INK)
            p = demo.phase(n, 0.6 + 0.22 * i, 1.9 + 0.22 * i)
            hit = value >= target
            shown = bullet_graph(cv, x, y, w, h, value, target, p, color=demo.TEAL if hit else demo.ACCENT)
            cv.mark(f'bullet-{i}', x, y, w, h)
            if p > 0:
                s = f'{shown:.0f}'
                vh = vb.text.block_size([s], value_f)[1]
                vb.text.draw(cv, [s], value_f, x + w + 30, y + (h - vh) / 2,
                             kit.mix(demo.MUTED, demo.TEAL if hit else demo.ACCENT, p))


TECHNIQUE = Technique(
    id='bullet-graph-fill',
    name='Bullet graph fill',
    family='broadcast',
    group='Charts',
    aliases=('bullet chart', 'target bar', 'bullet graph'),
    definition='A slim bar grows across stepped shaded bands toward its value, '
               'while a vertical tick shows the goal it is measured against.',
    phrasings=('a progress bar with a target line and shaded ranges behind it',
               'show each number filling up against its goal',
               'bars that grow and either reach the target mark or fall short'),
    related=('percentage-fill-bar', 'icon-line-to-fill', 'bookmark-fill', 'dot-density-map',
             'pencil-sketch', 'milestone-marker-pop'),
    api=('videobuilder.techniques.broadcast.bullet_graph_fill.bullet_graph',),
    demo=lambda: demo.film(draw),
)
