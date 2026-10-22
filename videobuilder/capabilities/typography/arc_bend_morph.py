"""Arc Bend Morph: a line of type bends onto a circular arc, its curve growing
from flat to a tall arch and relaxing back, each letter riding the curve and
tilting to follow it."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def arc_layout(text, font, bend):
    """Where each character of `text` sits when the line is bent by `bend`
    radians: the whole line spans that much of a circle (0 is flat, positive
    arches up like a rainbow, negative sags like a smile; 2*pi closes a ring).
    Returns `(char, dx, dy, angle)` per character, the offset of the glyph's
    centre from the line's middle and its rotation in radians. Arc length is
    kept, so the line is the same length at every bend."""
    total = vb.text.measure(text, font)
    out = []
    for i, ch in enumerate(text):
        x0 = vb.text.measure(text[:i], font) if i else 0.0
        s = x0 + (vb.text.measure(text[:i + 1], font) - x0) / 2 - total / 2  # kerning-aware centre
        if abs(bend) < 1e-6:
            out.append((ch, s, 0.0, 0.0))
            continue
        r = total / bend
        a = s / r
        out.append((ch, r * math.sin(a), r * (1 - math.cos(a)), a))
    return out


def draw_arc_text(cv, text, font, cx, cy, bend, color, alpha=1.0):
    """Draw `text` bent by `bend` radians (see `arc_layout`) with its middle
    letter centred at (cx, cy). Animate `bend` (e.g. `0 -> 2.4 -> 0` through an
    ease) for the morph. Returns the Box around the bent line."""
    lh = vb.text.line_height(font)
    xs, ys = [], []
    for ch, dx, dy, a in arc_layout(text, font, bend):
        w = vb.text.measure(ch, font)
        cv.ctx.save()
        cv.ctx.translate(cx + dx, cy + dy)
        cv.ctx.rotate(a)
        vb.text.draw(cv, [ch], font, -w / 2, -lh / 2, color, alpha=alpha)
        cv.ctx.restore()
        reach = math.hypot(w, lh) / 2
        xs += [cx + dx - reach, cx + dx + reach]
        ys += [cy + dy - reach, cy + dy + reach]
    if not xs:
        return vb.Box(cx, cy, 0, 0)
    return vb.Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def draw(n, cv):
    f = demo.font(76, 900)
    text = 'BEND THE LINE'
    up = vb.ease_in_out_quart(demo.phase(n, 0.4, 1.3))
    down = vb.ease_in_out_quart(demo.phase(n, 1.8, 2.7))
    bend = 2.6 * (up - down)
    cx, cy = demo.W / 2, demo.H / 2 - 50
    if abs(bend) > 1e-3:  # the faint guide circle the letters ride on
        total = vb.text.measure(text, f)
        r = total / bend
        cv.arc(cx, cy + r, r, -math.pi / 2 - bend * 0.56, -math.pi / 2 + bend * 0.56,
               demo.MUTED, width=3, alpha=0.35 * min(1.0, bend))
    box = draw_arc_text(cv, text, f, cx, cy, bend, demo.INK)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='arc-bend-morph',
    name='Arc bend morph',
    family='typography',
    group='Path and orbit',
    aliases=('text arc warp', 'curve bend animate', 'arc text', 'bend text'),
    definition='A straight line of lettering curls up into an arch, every letter tilting to follow the curve, '
               'then flattens out straight again.',
    phrasings=('make the headline curve into a rainbow shape and then go back to straight',
               'the words bend up along an arc and relax',
               'animate the text warping onto a curve'),
    related=('bend-deformer', 'twirl-warp-text', 'text-to-shape-morph', 'flight-arc', 'bezier-handle-bend',
             'line-to-polygon-transform'),
    api=('videobuilder.capabilities.typography.arc_bend_morph.draw_arc_text',
         'videobuilder.capabilities.typography.arc_bend_morph.arc_layout'),
    demo=lambda: demo.film(draw),
)
