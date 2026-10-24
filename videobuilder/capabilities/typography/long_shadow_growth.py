"""Long Shadow Growth: the same flat hard-edged diagonal shadow stretching
out as Long shadow extension (`../shapes/long_shadow_extension.py`, which
keeps the capability), on letters rather than a shape; they share the
aliases long shadow and flat long shadow. This module's own code stays (a
film may still import it), but it is no longer a capability of its own."""
import math

import videobuilder as vb

from .. import _demo as demo

MERGED_INTO = 'long-shadow-extension'


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
    f = demo.font(120, 900)
    lines = ['SHADOW']
    w, h = vb.text.block_size(lines, f)
    # Centre the word together with its fully grown shadow, so the tip stays in frame.
    length = 300
    reach = length * math.cos(math.radians(45))
    x, y = (demo.W - (w + reach)) / 2, (demo.H - (h + reach)) / 2
    grow = vb.ease_in_out_quart(demo.phase(n, 0.4, 2.4))
    box = draw_long_shadow(cv, lines, f, x, y, demo.INK, '#b8402f', length * grow, fade=demo.BG)
    cv.mark('text', *box)
