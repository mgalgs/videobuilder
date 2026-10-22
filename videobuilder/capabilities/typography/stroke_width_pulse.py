"""Stroke Width Pulse: outlined type whose line weight swells and thins on a
steady beat, so the letters seem to breathe while staying put."""
import math

from .. import _demo as demo
from ...compendium.components._transition_util import outline_text, text_path
from ..schema import Capability


def stroke_pulse(t, thin=2.0, thick=12.0, period=1.5, phase=0.0):
    """The stroke width at `t` seconds: a smooth cosine breath from `thin` up
    to `thick` and back once every `period` seconds, starting thin. `phase`
    (0 -> 1) shifts where in the breath `t = 0` falls."""
    k = 0.5 - 0.5 * math.cos(2 * math.pi * (t / period + phase))
    return thin + (thick - thin) * k


def draw_stroke_pulse(cv, line, font, cx, cy, t, color, **kw):
    """Draw `line` as outline type centred on (cx, cy), its stroke width
    breathing with `stroke_pulse(t, **kw)`. The letters are placed by their
    ink box, so they hold still while the line thickens. Returns the ink Box."""
    width = stroke_pulse(t, **kw)
    ink = text_path(cv, line, font, 0, 0)  # measure only
    cv.ctx.new_path()
    return outline_text(cv, line, font, cx - ink.w / 2, cy - ink.h / 2, color, width=width)


def draw(n, cv):
    box = draw_stroke_pulse(cv, 'BREATHE', demo.font(170, 900), demo.W / 2, demo.H / 2, n / demo.FPS,
                            demo.INK, thin=1.5, thick=14.0, period=1.5)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='stroke-width-pulse',
    name='Stroke width pulse',
    family='typography',
    group='Stroke and outline',
    aliases=('outline breathing', 'stroke weight pulse', 'line weight breathing',
             'stroke thickness oscillation', 'pulse outline'),
    definition='Hollow outlined lettering whose contour lines repeatedly grow heavier and then slim back down, '
               'like the word is slowly inhaling and exhaling.',
    phrasings=('make the outline of the title get thicker and thinner in a loop',
               'outlined text that breathes by swelling its stroke',
               'pulse the line weight on the hollow letters'),
    related=('outline-pulse-glow', 'scale-pulse', 'pulse-loader', 'line-draw-logo-reveal',
             'offset-path-expansion', 'icon-line-to-fill'),
    api=('videobuilder.capabilities.typography.stroke_width_pulse.draw_stroke_pulse',
         'videobuilder.capabilities.typography.stroke_width_pulse.stroke_pulse',
         'videobuilder.compendium.components._transition_util.outline_text'),
    demo=lambda: demo.film(draw),
)
