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


# The blend runs to an even mix, holds there (so the overlap -- and the gallery
# poster, taken at 2.1 s -- shows both faces at once), then settles on the serif.
BLEND = ((0.3, 1.1, 2.2, 2.7), (0, 0.5, 0.5, 1))
SMOOTH = vb.bezier(0.65, 0, 0.35, 1)


def draw(n, cv):
    p = vb.interpolate(n / demo.FPS, *BLEND, ease=SMOOTH)
    (name_a, face_a), (name_b, face_b) = FACES
    box = draw_typeface_crossfade(cv, 'Motion', face_a, face_b, demo.W / 2, demo.H / 2 - 30, p, demo.INK,
                                  ease=vb.linear)
    cv.mark('text', *box)
    # One fixed caption, side by side, each name lit by its face's share of the mix.
    label = demo.mono(30, 500)
    parts = ((name_a.upper(), 1 - p), ('\u2192', 0.5), (name_b.upper(), p))
    gap = 28
    widths = [vb.text.block_size([t], label)[0] for t, _ in parts]
    x = demo.W / 2 - (sum(widths) + gap * (len(parts) - 1)) / 2
    for (text, share), w in zip(parts, widths):
        demo.word(cv, text, x + w / 2, demo.H / 2 + 120, color=demo.TEAL, font=label, alpha=0.3 + 0.7 * share)
        x += w + gap


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
