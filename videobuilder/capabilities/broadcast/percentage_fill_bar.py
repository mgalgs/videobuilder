"""Percentage fill bar: a horizontal bar grows from the left to a stated
share of its track while a percentage figure rides along at the tip of the
fill, counting up to the final value as it goes."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def draw_percentage_bar(cv, x, y, w, h, value, p, font, fill=demo.ACCENT, track=demo.LINE, ink=demo.INK,
                        ease=vb.ease_out_quint, label='above', gap=8, radius=None):
    """A bar with its top-left at (x, y), `w` by `h`, filling towards
    `value` percent (0 -> 100) at progress `p` (0 -> 1, eased by `ease`).
    The figure shown is always the share currently filled, rounded, in
    `font` and `ink`; `label` puts it 'above' the tip, 'end' just past the
    tip, or None for no figure. `track` (or None) draws the empty bar
    behind. Returns the Box of the filled part."""
    r = h / 2 if radius is None else radius
    if track:
        cv.rect(x, y, w, h, track, radius=r)
    share = vb.clamp01(value / 100) * ease(vb.clamp01(p))
    fw = w * share
    if fw > 0:
        cv.rect(x, y, fw, h, fill, radius=min(r, fw / 2))
    if label:
        text = f'{round(share * 100)}%'
        tw, th = vb.text.block_size([text], font)
        if label == 'end':
            tx, ty = x + fw + gap, y + (h - th) / 2
        else:
            tx, ty = min(max(x + fw - tw / 2, x), x + w - tw), y - th - gap
        vb.text.draw(cv, [text], font, tx, ty, ink)
    return vb.Box(x, y, fw, h)


# The demo: four labelled rows filling one after another; the leader in a warm colour.
ROWS = (('Mobile', 64), ('Desktop', 41), ('Tablet', 87), ('TV', 23))
GOLD = '#f2b705'


def draw(n, cv):
    w, h, pitch = 600, 16, 92
    x = (demo.W - w) / 2 + 50
    top = (demo.H - pitch * (len(ROWS) - 1)) / 2 + 12
    name_f = demo.font(24, 700)
    pct_f = demo.font(20, 800)
    best = max(v for _, v in ROWS)
    for i, (name, value) in enumerate(ROWS):
        y = top + i * pitch
        p = demo.phase(n, 0.3 + 0.18 * i, 1.9 + 0.18 * i)
        color = GOLD if value == best else demo.ACCENT
        nw, nh = vb.text.block_size([name], name_f)
        vb.text.draw(cv, [name], name_f, x - 24 - nw, y + (h - nh) / 2, demo.MUTED)
        box = draw_percentage_bar(cv, x, y, w, h, value, p, pct_f, fill=color,
                                  ink=GOLD if value == best else demo.INK)
        if box.w > 0:
            cv.mark('bar', *box)


TECHNIQUE = Technique(
    id='percentage-fill-bar',
    name='Percentage fill bar',
    family='broadcast',
    group='Stats',
    aliases=('progress fill', 'meter bar', 'percent bar'),
    definition='A flat bar grows from the left across its track to a set share, '
               'with the percentage figure travelling at the tip and counting up as it fills.',
    phrasings=('show 64% as a bar that fills up with the number on the end',
               'a horizontal meter that slides out to each percentage',
               'animate the poll shares as bars growing with their percentages'),
    related=('scroll-progress-bar', 'poll-result-bar-fill', 'progress-ring', 'striped-progress-bar',
             'bar-chart-race', 'indeterminate-bar'),
    api=('videobuilder.techniques.broadcast.percentage_fill_bar.draw_percentage_bar',),
    demo=lambda: demo.film(draw),
)
