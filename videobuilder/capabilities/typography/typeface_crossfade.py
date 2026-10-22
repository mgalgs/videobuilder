"""Typeface Crossfade: one word stays put while its typeface changes, the old
face fading out over the new one fading in."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def draw_typeface_crossfade(cv, text, font_a, font_b, cx, cy, p, color, ease=vb.ease_in_out_quart):
    """Draw `text` centred at (cx, cy), set in `font_a` at `p` = 0 and in
    `font_b` at `p` = 1, the two faces cross-fading in between (`ease` shapes
    the blend). Each face is centred on its own measure, so a wider or
    narrower face swaps in without the word drifting. Returns the Box of the
    face that dominates at `p`."""
    k = ease(vb.clamp01(p))
    boxes = []
    for f, alpha in ((font_a, 1 - k), (font_b, k)):
        w, h = vb.text.block_size([text], f)
        box = vb.Box(cx - w / 2, cy - h / 2, w, h)
        if alpha > 0:
            vb.text.draw(cv, [text], f, box.x, box.y, color, alpha=alpha)
        boxes.append(box)
    return boxes[k >= 0.5]


FACES = (('Sans', demo.font(150, 800)), ('Serif', vb.Font('serif', 150, weight=700, style='italic')))


def draw(n, cv):
    p = demo.phase(n, 0.9, 2.1)
    (name_a, face_a), (name_b, face_b) = FACES
    box = draw_typeface_crossfade(cv, 'Motion', face_a, face_b, demo.W / 2, demo.H / 2 - 30, p, demo.INK)
    cv.mark('text', *box)
    label = demo.mono(30, 500)
    k = vb.ease_in_out_quart(p)
    for name, alpha in ((name_a, 1 - k), (name_b, k)):
        if alpha > 0:
            demo.word(cv, name.upper(), demo.W / 2, demo.H / 2 + 120, color=demo.TEAL, font=label, alpha=alpha)


CAPABILITY = Capability(
    id='typeface-crossfade',
    name='Typeface crossfade',
    family='typography',
    group='Variable font',
    aliases=('font family switch', 'font morph', 'font swap dissolve'),
    definition='A word holds its place while its lettering dissolves from one font into another, '
               'the two faces briefly overlapping mid-change.',
    phrasings=('fade the headline from a sans into a serif without moving it',
               'dissolve the same word between two different fonts',
               'swap the font on the title with a soft blend'),
    related=('theme-swap-crossfade', 'lyric-line-crossfade', 'cross-dissolve', 'per-character-fade-in',
             'glyph-cycling', 'typewriter-reveal'),
    api=('videobuilder.capabilities.typography.typeface_crossfade.draw_typeface_crossfade',),
    demo=lambda: demo.film(draw),
)
