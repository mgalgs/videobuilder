"""Radio Dot Scale: when a radio button is picked, its centre dot grows out
of nothing, swells a little past full size and settles, while the ring
takes on the accent colour."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def radio_dot_scale(p, ease=vb.ease_out_back):
    """Selection progress `p` (0 -> 1) -> the inner dot's scale, 0 at rest
    and 1 when selected, overshooting past 1 on the way with the default
    `ease`. Run `p` backwards (1 -> 0) to deselect."""
    return max(0.0, ease(vb.clamp01(p)))


def draw_radio(cv, cx, cy, p, r=40, color=demo.ACCENT, idle=demo.MUTED, ring=4, dot=0.5, ease=vb.ease_out_back):
    """A radio button of outer radius `r` centred at (cx, cy), `p` of the
    way (0 -> 1) through being selected: the ring fades from `idle` to
    `color` and the inner dot, `dot` of the ring's radius when settled,
    scales in by `radio_dot_scale`. Returns the button's Box."""
    p = vb.clamp01(p)
    tint = vb.clamp01(p * 2.5)  # the ring has turned before the dot has finished landing
    cv.arc(cx, cy, r - ring / 2, 0, 2 * math.pi, idle, width=ring, alpha=0.8 * (1 - tint))
    cv.arc(cx, cy, r - ring / 2, 0, 2 * math.pi, color, width=ring, alpha=tint)
    s = radio_dot_scale(p, ease)
    if s > 0:
        demo.dot(cv, cx, cy, r * dot * s, color)
    return vb.Box(cx - r, cy - r, 2 * r, 2 * r)


OPTIONS = ('Standard', 'Express', 'Overnight')


def draw(n, cv):
    # Pick "Express", then move the choice to "Overnight": each pick pops its dot in.
    picks = ((1, 0.5), (2, 1.8))
    f = demo.font(52, 700)
    r, gap = 40, 150
    top = demo.H / 2 - gap
    x = demo.W / 2 - 220
    for i, label in enumerate(OPTIONS):
        y = top + i * gap
        p = 0.0
        for k, (idx, t) in enumerate(picks):
            if idx == i:
                p = demo.phase(n, t, t + 0.45)
            if k + 1 < len(picks) and idx == i:  # handed on: shrink back out quickly
                p *= 1 - demo.phase(n, picks[k + 1][1], picks[k + 1][1] + 0.15)
        box = draw_radio(cv, x, y, p, r=r)
        cv.mark(f'radio-{i}', *box)
        _, h = vb.text.block_size([label], f)
        vb.text.draw(cv, [label], f, x + r + 40, y - h / 2, demo.INK if p > 0 else demo.MUTED)


CAPABILITY = Capability(
    id='radio-dot-scale',
    name='Radio dot scale',
    family='ui',
    group='Toggles & controls',
    aliases=('radio pop', 'selected dot scale'),
    definition='Picking a radio option makes the dot inside its ring grow from a point, '
               'swell slightly too big and settle at its final size.',
    phrasings=('the radio button dot pops in when you select it',
               'make the selected option\'s circle bounce into the ring',
               'a springy fill dot when choosing one of the options'),
    related=('circle-pop', 'halftone-dot-scaling', 'dot-density-map', 'character-scale-in', 'bouncing-dots',
             'dot-grid-displacement'),
    api=('videobuilder.capabilities.ui.radio_dot_scale.draw_radio',
         'videobuilder.capabilities.ui.radio_dot_scale.radio_dot_scale',
         'videobuilder.ease_out_back'),
    demo=lambda: demo.film(draw),
)
