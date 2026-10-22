"""Scale Pulse: a word swells a little larger and settles back to its
resting size over and over, in time, scaled about its own centre."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def pulse_scale(t, period=1.0, amount=0.15, attack=0.3):
    """The scale factor at `t` seconds of a pulse that repeats every `period`
    seconds: up from 1 to `1 + amount` over the first `attack` of each beat
    (easing out), then back down to 1 over the rest (easing in and out).
    Lock `period` to `60 / bpm` to pulse on a beat."""
    u = (t / period) % 1.0
    if u < attack:
        k = math.sin(u / attack * math.pi / 2)
    else:
        k = 0.5 + 0.5 * math.cos((u - attack) / (1 - attack) * math.pi)
    return 1 + amount * k


def draw_scale_pulse(cv, text, font, cx, cy, t, color, alpha=1.0, **kw):
    """Draw `text` on one line centred at (cx, cy), scaled about that centre
    by `pulse_scale(t, **kw)`. Returns the Box of the line as drawn this frame."""
    s = pulse_scale(t, **kw)
    w, h = vb.text.block_size([text], font)
    with cv.layer(dx=cx * (1 - s), dy=cy * (1 - s), scale=s):
        vb.text.draw(cv, [text], font, cx - w / 2, cy - h / 2, color, alpha=alpha)
    return vb.Box(cx - w * s / 2, cy - h * s / 2, w * s, h * s)


def draw(n, cv):
    box = draw_scale_pulse(cv, 'PULSE', demo.font(150, 800), demo.W / 2, demo.H / 2, n / demo.FPS,
                           demo.INK, period=1.0, amount=0.18)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='scale-pulse',
    name='Scale pulse',
    family='typography',
    group='Stretch and squash',
    aliases=('heartbeat text', 'breathing type', 'text pulse'),
    definition='A word repeatedly swells slightly bigger and shrinks back to its normal size about its centre, '
               'like a steady heartbeat.',
    phrasings=('make the title throb in and out',
               'have the word beat like a heart',
               'the text gently grows and shrinks on a loop to draw the eye'),
    related=('stroke-width-pulse', 'pulse-loader', 'scale-tile-wave', 'like-heart-burst', 'live-indicator-pulse',
             'character-scale-in'),
    api=('videobuilder.capabilities.typography.scale_pulse.draw_scale_pulse',
         'videobuilder.capabilities.typography.scale_pulse.pulse_scale'),
    demo=lambda: demo.film(draw),
)
