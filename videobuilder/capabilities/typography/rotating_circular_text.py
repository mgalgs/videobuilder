"""Rotating circular text: a line of lettering set around a circle, each
glyph upright to the ring, with the whole ring turning slowly about its
centre -- the spinning badge or stamp."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def ring_text(text, font, radius, fill=True, sep='  •  '):
    """The characters to set around a ring of `radius`. With `fill`, `text`
    and `sep` repeat as many whole times as fit the circumference, so the
    ring closes on itself; otherwise `text` alone."""
    if not fill:
        return text
    unit = text + sep
    reps = max(1, int(2 * math.pi * radius / vb.text.measure(unit, font)))
    return unit * reps


def draw_circular_text(cv, text, font, cx, cy, radius, turn, color, spread=None, inward=False,
                       color_of=None, alpha=1.0):
    """Draw `text` around a circle of `radius` centred at (cx, cy), the
    middle of each glyph on the circle and its baseline tangent to it.

    `turn` is the ring's rotation in radians (0 starts the text at the top,
    reading clockwise); animate it for the spin, e.g. `2 * math.pi * t /
    period`. `spread` is the arc the text covers in radians (default: the
    whole circle, glyphs spaced by their widths). `inward` sets the letters
    with their tops toward the centre, reading counter-clockwise along the
    bottom. `color_of(ch)` may return a per-character colour (None keeps
    `color`). Returns the Box of the ring."""
    widths = [vb.text.measure(ch, font) for ch in text]
    total = sum(widths) or 1.0
    spread = 2 * math.pi if spread is None else spread
    lh = vb.text.line_height(font)
    ctx = cv.ctx
    sign = -1 if inward else 1
    at = 0.0
    for ch, w in zip(text, widths):
        mid = (at + w / 2) / total
        at += w
        if ch.isspace():
            continue
        a = turn - math.pi / 2 + sign * spread * mid
        ctx.save()
        ctx.translate(cx + radius * math.cos(a), cy + radius * math.sin(a))
        ctx.rotate(a + sign * math.pi / 2)
        vb.text.draw(cv, [ch], font, -w / 2, -lh / 2, (color_of and color_of(ch)) or color, alpha=alpha)
        ctx.restore()
    outer = radius + lh / 2
    return vb.Box(cx - outer, cy - outer, 2 * outer, 2 * outer)


RADIUS = 175
PERIOD = 8.0  # seconds a full turn takes: well over a third of a turn across the demo
LINE = 'ALL THE WAY AROUND \u2022 ROTATING TYPE \u2022 '  # once round, no repeat, so the turn reads


def draw(n, cv):
    cx, cy = demo.W / 2, demo.H / 2
    f = demo.font(40, 800, tracking=0.1)
    text = LINE
    lh = vb.text.line_height(f)
    for r in (RADIUS - lh * 0.8, RADIUS + lh * 0.8):
        cv.arc(cx, cy, r, 0, 2 * math.pi, demo.LINE, width=2)
    demo.dot(cv, cx, cy, r=92, color=demo.ACCENT)
    demo.word(cv, '360°', cx, cy, size=48, color=demo.BG)
    turn = 2 * math.pi * (n / demo.FPS) / PERIOD
    box = draw_circular_text(cv, text, f, cx, cy, RADIUS, turn, demo.INK,
                             color_of=lambda ch: demo.TEAL if ch == '•' else None)
    cv.mark('ring', *box)


CAPABILITY = Capability(
    id='rotating-circular-text',
    name='Rotating circular text',
    family='typography',
    group='Path and orbit',
    aliases=('circular text', 'text on a circle', 'spinning text badge', 'rotating badge', 'text ring'),
    definition='Lettering wrapped around a circle, each glyph standing on the ring, while the whole ring '
               'turns steadily about its centre.',
    phrasings=('words going round in a circle that keeps spinning',
               'a spinning badge with the text around the edge',
               'put the slogan on a ring and have it slowly rotate around the logo'),
    related=('spinner-ring', 'rotating-rings', 'letter-roll', 'highlight-circle-draw', 'character-rotate-in',
             'progress-ring'),
    api=('videobuilder.capabilities.typography.rotating_circular_text.draw_circular_text',
         'videobuilder.capabilities.typography.rotating_circular_text.ring_text'),
    demo=lambda: demo.film(draw),
)
