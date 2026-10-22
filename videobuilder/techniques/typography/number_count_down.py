"""Number count-down: a number steps down one whole value at a time, from a
start value to zero, each new value landing with a small pop."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def countdown(t, start=10, step=1.0, end=0):
    """The value shown `t` seconds into a count-down from `start` to `end`,
    dropping by one every `step` seconds, and how far (0 -> 1) the current
    value is through its own tick. Before 0 it holds `start` at rest (progress
    1); once it reaches `end` it stays there, progress capped at 1."""
    if t < 0:
        return start, 1.0
    ticks = min(math.floor(t / step), start - end)
    return start - ticks, min((t - ticks * step) / step, 1.0)


def draw_countdown(cv, t, font, cx, cy, color, start=10, step=1.0, end=0, digits=2, pop=0.18,
                   settle=0.35, final_color=None):
    """Draw the count-down's value at `t` seconds, zero-padded to `digits`,
    centred at (cx, cy). Each new value starts `pop` larger and eases back to
    size over the first `settle` of its tick, so every step reads as a beat.
    The last value uses `final_color` when given. Returns the Box of the
    number at rest."""
    value, p = countdown(t, start, step, end)
    shown = f'{value:0{digits}d}'
    w, h = vb.text.block_size([shown], font)
    s = 1 + pop * (1 - vb.ease_out_quint(vb.clamp01(p / settle)))
    ink = final_color if final_color and value == end else color
    with cv.layer(dx=cx * (1 - s), dy=cy * (1 - s), scale=s):
        vb.text.draw(cv, [shown], font, cx - w / 2, cy - h / 2, ink)
    return vb.Box(cx - w / 2, cy - h / 2, w, h)


def draw(n, cv):
    box = draw_countdown(cv, n / demo.FPS - 0.2, demo.font(260, 800), demo.W / 2, demo.H / 2, demo.INK,
                         start=5, step=0.5, final_color=demo.ACCENT)
    cv.mark('number', *box)


TECHNIQUE = Technique(
    id='number-count-down',
    name='Number count-down',
    family='typography',
    group='Counting',
    aliases=('countdown timer', 'reverse counter', 'countdown clock', 'count-down display'),
    definition='A big number drops by one at a steady beat, 5, 4, 3, 2, 1, until it reaches zero.',
    phrasings=('a number that counts down to zero',
               'show a countdown from ten before it starts',
               'a timer ticking down the last few seconds'),
    related=('stopwatch-count-up', 'game-clock-countdown', 'timecode-counter', 'odometer-roll',
             'seven-segment-display', 'badge-count-bump'),
    api=('videobuilder.techniques.typography.number_count_down.draw_countdown',
         'videobuilder.techniques.typography.number_count_down.countdown'),
    demo=lambda: demo.film(draw),
)
