"""Outline Pulse Glow: letters drawn as a thin coloured outline, with a soft
halo of the same colour around them that swells and fades like slow breathing."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ...canvas import rgba
from ...type import kit


def pulse(t, period=1.4, low=0.15, high=1.0, offset=0.0):
    """The glow's strength at `t` seconds: a smooth cosine breath from `low`
    up to `high` and back every `period` seconds, at `low` when `t` is
    `offset`."""
    k = (1 - math.cos(2 * math.pi * (t - offset) / period)) / 2
    return low + (high - low) * k


def draw_outline_glow(cv, s, font, x, y, color, glow, width=2.5, radius=16, fill=None):
    """Draw `s` from its top-left (x, y) as an outline of `width` px in
    `color`, haloed by a blur of that outline whose strength is `glow`
    (0 = none, 1 = full; feed it `pulse(t)` to make it breathe). The halo is
    two blurs, a wide one of `radius` px and a tight one a quarter of that,
    and the outline itself brightens a little with `glow`. `fill`, if given,
    paints the letters' insides first. Returns the Box of the line."""
    glow = vb.clamp01(glow)
    box = kit.line_box(x, y, s, font)

    def stroke(sub, w):
        ctx = sub.ctx
        ctx.save()
        ctx.translate(x, y)
        ctx.new_path()
        ctx.append_path(kit._outline(s, font))
        ctx.set_source_rgba(*rgba(color))
        ctx.set_line_width(w)
        ctx.set_line_join(1)  # round
        ctx.stroke()
        ctx.restore()

    if fill is not None:
        kit.glyphs(cv, s, font, x, y, fill)
    if glow > 0:
        kit.blurred(cv, box, radius, lambda sub: stroke(sub, width * 3), alpha=0.9 * glow)
        kit.blurred(cv, box, radius / 4, lambda sub: stroke(sub, width * 1.5), alpha=glow)
    with cv.layer(opacity=0.55 + 0.45 * glow):
        stroke(cv, width)
    return box


def draw(n, cv):
    f = demo.font(190, 900)
    text = 'GLOW'
    w, h = vb.text.block_size([text], f)
    box = draw_outline_glow(cv, text, f, (demo.W - w) / 2, (demo.H - h) / 2, '#8c7bff',
                            pulse(n / demo.FPS, period=1.5, low=0.05), width=3, radius=22)
    cv.mark('text', *box)


TECHNIQUE = Technique(
    id='outline-pulse-glow',
    name='Outline pulse glow',
    family='typography',
    group='Surface and light',
    aliases=('neon glow pulse', 'soft glow breathing', 'glowing outline text'),
    definition='Text drawn as a thin coloured outline whose soft halo of light slowly swells '
               'and fades again, so the letters seem to breathe.',
    phrasings=('make the outlined title glow brighter and dimmer on a loop',
               'hollow letters with a neon halo that gently pulses',
               'a breathing glow around the edges of the words'),
    related=('stroke-width-pulse', 'neon-flicker', 'glow-button', 'border-glow-follow',
             'per-character-fade-in', 'light-trail-logo-reveal'),
    api=('videobuilder.techniques.typography.outline_pulse_glow.draw_outline_glow',
         'videobuilder.techniques.typography.outline_pulse_glow.pulse'),
    demo=lambda: demo.film(draw),
)
