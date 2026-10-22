"""Character slide-in: the letters of a word glide in sideways, one after
another, each coming to rest in its own place on the line."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def slide_offsets(text, p, distance, side='right', stagger=0.6, ease=vb.ease_out_quint):
    """Each character's `(dx, k)` at progress `p` (0 -> 1): `dx` is how far it
    still sits from its resting x, `k` its own eased progress. The leading
    character -- the first when sliding in from the right, the last from
    the left -- starts at 0; the starts spread over the first `stagger` of
    the reveal and each character takes the rest, so the last lands at 1."""
    n = len(text)
    sign = 1 if side == 'right' else -1
    each = 1 - stagger
    out = []
    for i in range(n):
        order = i if side == 'right' else n - 1 - i
        start = stagger * order / max(1, n - 1)
        k = ease(vb.clamp01((p - start) / each))
        out.append((sign * distance * (1 - k), k))
    return out


def draw_slide_in(cv, text, font, x, y, p, color, side='right', distance=None, fade=True, **kw):
    """Draw `text` from its top-left (x, y) with its characters sliding in
    from `side` ('right' or 'left') at progress `p`. `distance` is how far
    each starts from its place (default three times the font size); with
    `fade` a character fades up over its slide. `kw` goes to `slide_offsets`
    (`stagger`, `ease`). Returns the Box of the finished line."""
    distance = 3 * font.size if distance is None else distance
    left = x
    for ch, (dx, k) in zip(text, slide_offsets(text, p, distance, side=side, **kw)):
        alpha = vb.clamp01(k * 1.6) if fade else 1.0
        if alpha > 0 and not ch.isspace():
            vb.text.draw(cv, [ch], font, left + dx, y, color, alpha=alpha)
        left += vb.text.measure(ch, font)
    w, h = vb.text.block_size([text], font)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    f = demo.font(150, 800)
    text = 'MOTION'
    w, h = vb.text.block_size([text], f)
    x, y = (demo.W - w) / 2, (demo.H - h) / 2
    box = draw_slide_in(cv, text, f, x, y, demo.phase(n, 0.3, 2.2), demo.INK, distance=520)
    cv.mark('text', *box)


TECHNIQUE = Technique(
    id='character-slide-in',
    name='Character slide-in',
    family='typography',
    group='Per-unit reveals',
    aliases=('letter slide from side', 'horizontal character slide', 'staggered letter slide'),
    definition='The letters of a word travel in sideways from one edge, each setting off a beat after '
               'its neighbour and easing to a stop in its slot.',
    phrasings=('have the title glide in from the side one letter at a time',
               'letters slide across into place in a quick cascade',
               'each character slides in horizontally, staggered'),
    related=('letter-sort-animation', 'word-carousel-rotate', 'letter-roll', 'hover-letter-displacement',
             'letter-morph', 'character-3d-flip'),
    api=('videobuilder.techniques.typography.character_slide_in.draw_slide_in',
         'videobuilder.techniques.typography.character_slide_in.slide_offsets'),
    demo=lambda: demo.film(draw),
)
