"""Long Shadow Growth: a flat, hard-edged shadow streams out of the letters
at a fixed angle, stretching from nothing to a long diagonal trail."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def _mix(a, b, t):
    a, b = vb.rgba(a), vb.rgba(b)
    return tuple(round(255 * (x + (y - x) * t)) for x, y in zip(a[:3], b[:3])) + (a[3] + (b[3] - a[3]) * t,)


def draw_long_shadow(cv, lines, font, x, y, color, shadow, length, angle=45, fade=None, alpha=1.0):
    """Draw `lines` (a list of strings, as `vb.text.draw` takes) from the
    top-left (x, y) in `color`, over a flat long shadow `length` px long
    heading `angle` degrees below the horizontal (45 = down and right).
    The shadow is the text stamped once per device pixel along that line,
    farthest first, so it reads as one solid shape; with `fade` its colour
    runs from `shadow` at the letters to `fade` (usually the background) at
    the tip. Animate `length` to grow it. Returns the text's Box."""
    a = math.radians(angle)
    ux, uy = math.cos(a), math.sin(a)
    step = 1 / max(cv.scale_factor(), 1e-6)
    count = int(max(length, 0) / step)
    with cv.layer(opacity=alpha):
        for i in range(count, 0, -1):
            d = i * step
            c = shadow if fade is None else _mix(shadow, fade, d / max(length, 1e-6))
            vb.text.draw(cv, lines, font, x + ux * d, y + uy * d, c)
        return vb.text.draw(cv, lines, font, x, y, color)


def draw(n, cv):
    f = demo.font(150, 900)
    lines = ['SHADOW']
    w, h = vb.text.block_size(lines, f)
    x, y = (demo.W - w) / 2 - 120, (demo.H - h) / 2 - 120
    grow = vb.ease_in_out_quart(demo.phase(n, 0.4, 2.4))
    box = draw_long_shadow(cv, lines, f, x, y, demo.INK, '#b8402f', 380 * grow, fade=demo.BG)
    cv.mark('text', *box)


TECHNIQUE = Technique(
    id='long-shadow-growth',
    name='Long shadow growth',
    family='typography',
    group='Shadow',
    aliases=('long shadow', 'flat long shadow', 'growing long shadow', 'shadow extend'),
    definition='A flat, sharp-edged shadow slides out of the letters along a diagonal, '
               'lengthening until it trails far across the frame.',
    phrasings=('make the title cast a long diagonal shadow that stretches out',
               'flat design text where the shadow grows longer behind it',
               'the shadow should extend out from the words at 45 degrees'),
    related=('long-shadow-extension', 'drop-shadow-breathing', 'character-rise', 'extrusion-depth-reveal',
             'shadow-play', 'outline-pulse-glow'),
    api=('videobuilder.techniques.typography.long_shadow_growth.draw_long_shadow',),
    demo=lambda: demo.film(draw),
)
