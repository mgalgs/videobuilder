"""Character Rotate-in: each letter swings upright about its own pivot from
a tilted, faded start, one after another along the line."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ...type import kit as type_kit


def rotate_in(text, p, angle=-90.0, stagger=0.6, ease=vb.ease_out_back):
    """`text` at progress `p` (0 -> 1) as `(char, degrees, alpha)` triples.
    Each letter turns from `angle` degrees to 0 under `ease`; the letters
    start one after another across the first `stagger` of the reveal, the
    last finishing at 1. Alpha comes up over the first third of each turn."""
    n = max(1, len(text))
    span = 1 - stagger
    out = []
    for i, ch in enumerate(text):
        start = stagger * i / max(1, n - 1)
        q = vb.clamp01((p - start) / span)
        out.append((ch, angle * (1 - ease(q)), vb.clamp01(q * 3)))
    return out


def draw_rotate_in(cv, text, font, x, y, p, color, pivot='bottom', **kw):
    """Draw `text` rotating in at progress `p` from its top-left (x, y). Each
    letter turns about its own `pivot`: 'bottom' (the foot of the letter, so
    it swings up like a hinge) or 'center' (spins in place). Letters keep
    their final places, so the line never shifts. `kw` goes to `rotate_in`.
    Returns the Box of the finished line."""
    ctx = cv.ctx
    lh = vb.text.line_height(font)
    left = x
    for ch, deg, alpha in rotate_in(text, p, **kw):
        adv = vb.text.measure(ch, font)
        if alpha > 0 and not ch.isspace():
            px, py = left + adv / 2, y + (lh * 0.8 if pivot == 'bottom' else lh / 2)
            ctx.save()
            ctx.translate(px, py)
            ctx.rotate(math.radians(deg))
            type_kit.glyphs(cv, ch, font, -adv / 2, y - py, color, alpha)
            ctx.restore()
        left += adv
    w, h = vb.text.block_size([text], font)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    f = demo.font(130, 800)
    text = 'ROTATE IN'
    w, h = vb.text.block_size([text], f)
    box = draw_rotate_in(cv, text, f, (demo.W - w) / 2, (demo.H - h) / 2, demo.phase(n, 0.3, 2.3), demo.INK)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='character-rotate-in',
    name='Character rotate-in',
    family='typography',
    group='Per-unit reveals',
    aliases=('letter rotate in', 'per-character rotation', 'rotating letters reveal'),
    definition='Letters appear one at a time, each turning upright from a tipped-over angle '
               'as it fades in, until the whole word stands straight.',
    phrasings=('each letter swings up into place one by one',
               'the title letters spin in individually and settle upright',
               'make the characters rotate into position in sequence'),
    related=('character-3d-flip', 'orbiting-characters', 'spin', 'letter-sort-animation', 'glyph-cycling',
             'word-carousel-rotate'),
    api=('videobuilder.capabilities.typography.character_rotate_in.draw_rotate_in',
         'videobuilder.capabilities.typography.character_rotate_in.rotate_in'),
    demo=lambda: demo.film(draw),
)
