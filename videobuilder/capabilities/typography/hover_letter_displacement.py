"""Hover letter displacement: a pointer passes along a word, and the letter
under it rises and grows, its neighbours following less and less with
distance, so a soft bump rides along the line with the pointer."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ...type import kit as type_kit

# An arrow pointer, tip at (0, 0), in pixels at scale 1.
POINTER = ((0, 0), (0, 27), (7, 21), (12, 32), (17.5, 29.5), (12.5, 19), (21, 19))


def influence(dx, dy=0.0, radius=120.0, reach=160.0):
    """How strongly a letter whose centre is (dx, dy) from the pointer
    responds, 0 -> 1: a Gaussian bump `radius` wide across the line, faded
    out as the pointer moves more than `reach` above or below it."""
    across = math.exp(-0.5 * (dx / radius) ** 2)
    off = vb.clamp01(1 - abs(dy) / reach) if reach else 1.0
    return across * off * off * (3 - 2 * off)


def draw_hover_letters(cv, text, font, x, y, pointer, color, hot=None, lift=60.0, grow=0.35,
                       radius=None, reach=None, alpha=1.0):
    """Draw `text` from its top-left (x, y), each letter lifted by up to
    `lift` px and scaled by up to `1 + grow` about its baseline centre,
    in proportion to `influence` from `pointer` (an (x, y), or None for
    the resting line). `hot` tints the letters toward that colour as they
    lift. `radius` defaults to most of a letter, `reach` to
    the line height. Returns the Box of the resting line."""
    xs, width = type_kit.advances(text, font)
    lh = vb.text.line_height(font)
    radius = radius or 0.8 * width / max(len(text), 1)
    reach = reach or 1.6 * lh
    base = y + lh * 0.8
    for ch, cx0 in zip(text, xs):
        if ch.isspace():
            continue
        adv = vb.text.measure(ch, font)
        cx = x + cx0 + adv / 2
        k = 0.0 if pointer is None else influence(pointer[0] - cx, pointer[1] - (y + lh / 2), radius, reach)
        s = 1 + grow * k
        ink = color if hot is None or k <= 0 else type_kit.mix(color, hot, k)
        with cv.layer(dx=cx * (1 - s), dy=base * (1 - s) - lift * k, scale=s):
            vb.text.draw(cv, [ch], font, x + cx0, y, ink, alpha=alpha)
    return vb.Box(x, y, width, lh)


def draw_pointer(cv, x, y, scale=1.0, color=demo.INK, edge=demo.BG):
    """An arrow pointer with its tip at (x, y)."""
    pts = [(x + px * scale, y + py * scale) for px, py in POINTER]
    cv.shape_shadow(pts, dx=2, dy=4, blur=6, color=(0, 0, 0, 0.45))
    c = cv.ctx
    c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    c.close_path()
    c.set_source_rgba(*vb.rgba(color))
    c.fill_preserve()
    c.set_source_rgba(*vb.rgba(edge))
    c.set_line_width(2)
    c.stroke()


def draw(n, cv):
    f = demo.font(150, 900)
    text = 'MOTION'
    w, h = vb.text.block_size([text], f)
    x, y = (demo.W - w) / 2, (demo.H - h) / 2 + 40
    # The pointer comes in from below left, sweeps along under the word, then drops away so the word settles.
    p = demo.phase(n, 0.1, 2.4)
    px = x - 40 + (w + 80) * (0.5 - 0.5 * math.cos(math.pi * p))
    py = y + h * 0.9 + 80 * (1 - math.sin(math.pi * p) ** 0.4) + 220 * vb.ease_in_out_quart(demo.phase(n, 2.3, 2.9))
    box = draw_hover_letters(cv, text, f, x, y, (px, py), demo.INK, hot=demo.ACCENT, lift=70, grow=0.25)
    cv.mark('text', *box)
    draw_pointer(cv, px, py, scale=1.6)


CAPABILITY = Capability(
    id='hover-letter-displacement',
    name='Hover letter displacement',
    family='typography',
    group='Web and scroll',
    aliases=('interactive letter hover', 'letter lift on hover'),
    definition='As a pointer moves along a word, the letter nearest it rises and swells while '
               'the letters beside it lift a little less, so a soft wave follows the pointer.',
    phrasings=('letters pop up as the mouse moves over the word',
               'the cursor pushes each letter up as it slides past',
               'hovering over the headline makes the nearby letters jump and grow'),
    related=('spring-drag-letters', 'hover-lift', 'dot-grid-displacement', 'character-slide-in',
             'bouncing-dots', 'letter-roll'),
    api=('videobuilder.capabilities.typography.hover_letter_displacement.draw_hover_letters',
         'videobuilder.capabilities.typography.hover_letter_displacement.influence',
         'videobuilder.capabilities.typography.hover_letter_displacement.draw_pointer'),
    demo=lambda: demo.film(draw),
)
