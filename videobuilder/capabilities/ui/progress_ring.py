"""Progress Ring: a thick circular stroke that fills clockwise from the top
over a faint full-circle track, showing how much of a task is done."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

TOP = -math.pi / 2  # canvas angles run clockwise from 3 o'clock


def draw_progress_ring(cv, cx, cy, r, p, color, track=None, width=18, start=TOP, round_caps=True, alpha=1.0):
    """A ring centred at (cx, cy), radius `r` to the middle of the stroke,
    filled clockwise from `start` to fraction `p` (0 -> 1, clamped). `track`
    is the colour of the unfilled full circle under it (None: no track).
    Round caps give the filled arc soft ends, as a UI loader has. Returns the
    angle the fill reaches, for anything that rides its leading end."""
    p = vb.clamp01(p)
    end = start + 2 * math.pi * p
    ctx = cv.ctx
    if track is not None:
        cv.arc(cx, cy, r, 0, 2 * math.pi, track, width=width, alpha=alpha)
    if p > 0:
        ctx.save()
        if round_caps and p < 1:
            ctx.set_line_cap(1)  # round
        cv.arc(cx, cy, r, start, end, color, width=width, alpha=alpha)
        ctx.restore()
    return end


def draw(n, cv):
    cx, cy, r, w = demo.W / 2, demo.H / 2, 190, 26
    p = vb.ease_in_out_quart(demo.phase(n, 0.3, 2.5))
    draw_progress_ring(cv, cx, cy, r, p, demo.ACCENT, track=demo.LINE, width=w)
    box = demo.word(cv, f'{round(p * 100)}%', cx, cy, size=88, font=demo.mono(88, 700))
    cv.mark('ring', cx - r - w / 2, cy - r - w / 2, 2 * r + w, 2 * r + w)
    cv.mark('percent', *box)


TECHNIQUE = Technique(
    id='progress-ring',
    name='Progress ring',
    family='ui',
    group='Loaders',
    aliases=('circular progress', 'radial progress', 'ring progress', 'radial progress ring', 'arc sweep meter'),
    definition='A thick circular stroke sweeps clockwise around a faint track, from empty toward full, '
               'to show how far along something is.',
    phrasings=('a circle that fills up as the loading goes',
               'a round progress bar that sweeps to 100 percent',
               'a ring that closes around the percentage in the middle'),
    related=('rotating-rings', 'highlight-circle-draw', 'chord-diagram-draw', 'rotating-circular-text',
             'percentage-fill-bar', 'cycle-diagram-rotation'),
    api=('videobuilder.techniques.ui.progress_ring.draw_progress_ring',),
    demo=lambda: demo.film(draw),
)
