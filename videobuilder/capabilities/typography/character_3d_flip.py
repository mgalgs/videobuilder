"""Character 3D flip: each letter turns half a revolution about its own
vertical axis, one after another, and lands showing its back face -- a new
colour, or a different letter."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def flip_angles(count, p, stagger=0.55, ease=vb.ease_in_out_quart):
    """The turn of each of `count` characters at progress `p` (0 -> 1), in
    radians from 0 (front face) to pi (back face). Character `i` starts its
    turn at `stagger * i / (count - 1)` and every turn takes the rest of the
    run, so the last one lands at 1."""
    span = 1 - stagger
    out = []
    for i in range(count):
        start = stagger * i / (count - 1) if count > 1 else 0.0
        out.append(math.pi * ease(vb.clamp01((p - start) / span)))
    return out


def draw_char_flip(cv, text, font, x, y, p, front, back, back_text=None, depth=0.12, shade=0.35, **kw):
    """Draw `text` from its top-left (x, y) with every character flipping at
    progress `p`: until its turn passes edge-on it shows its front face in
    `front`, then its back face in `back`, using the same position's
    character of `back_text` if given (else the same letter). The turn is
    drawn as a horizontal squash, with the letter swelling by `depth` and
    dimming by `shade` as it goes edge-on, which reads as perspective. Each
    back character is centred on its front one's slot, so the line keeps its
    spacing. `kw` goes to `flip_angles`. Returns the Box of the front line."""
    back_text = text if back_text is None else back_text.ljust(len(text))[:len(text)]
    _, h = vb.text.block_size([text], font)
    left = x
    ctx = cv.ctx
    for ch, alt, a in zip(text, back_text, flip_angles(len(text), p, **kw)):
        adv = vb.text.measure(ch, font)
        cx, cy = left + adv / 2, y + h / 2
        left += adv
        glyph, color = (ch, front) if a < math.pi / 2 else (alt, back)
        if glyph.isspace():
            continue
        side = math.sin(a)
        sx = max(abs(math.cos(a)), 0.02)  # never fully vanish: a sliver shows the edge
        gw = vb.text.measure(glyph, font)
        ctx.save()
        ctx.translate(cx, cy)
        ctx.scale(sx, 1 + depth * side)
        vb.text.draw(cv, [glyph], font, -gw / 2, -h / 2, color, alpha=1 - shade * side)
        ctx.restore()
    w, _ = vb.text.block_size([text], font)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    f = demo.font(150, 900, tracking=0.08)
    text = 'MOTION'
    w, h = vb.text.block_size([text], f)
    box = draw_char_flip(cv, text, f, (demo.W - w) / 2, (demo.H - h) / 2, demo.phase(n, 0.4, 2.5),
                         demo.INK, demo.TEAL)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='character-3d-flip',
    name='Character 3D flip',
    family='typography',
    group='Depth and 3D',
    aliases=('card flip letters', 'rotateY letter flip', 'letter flip'),
    definition='Letters turn over one at a time about an upright axis, like cards, and land showing '
               'their reverse side in a new colour or as a new letter.',
    phrasings=('flip each letter over one by one so the word changes colour',
               'the characters spin around like cards and come back as different letters',
               'a ripple of letters turning over in 3D across the title'),
    related=('flip', 'logo-3d-spin-reveal', 'character-rotate-in', 'word-flip-in', 'tile-flip', 'coin-flip'),
    api=('videobuilder.capabilities.typography.character_3d_flip.draw_char_flip',
         'videobuilder.capabilities.typography.character_3d_flip.flip_angles'),
    demo=lambda: demo.film(draw),
)
