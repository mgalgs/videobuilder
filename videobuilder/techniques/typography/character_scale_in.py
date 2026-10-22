"""Character Scale-in: the letters of a line appear one after another, each
growing from nothing to full size about its own centre, so the word pops in
from left to right."""
import videobuilder as vb
from videobuilder.type import kit as type_kit

from .. import _demo as demo
from ..schema import Technique


def char_scales(text, p, overlap=4.0, ease=vb.ease_out_back):
    """The scale of each character of `text` at progress `p` (0 -> 1). The
    letters start in turn; each one's grow lasts `overlap` letters' worth of
    the stagger, so several are growing at once, and the last reaches full
    size at 1. `ease` shapes each grow (default: a little overshoot). Spaces
    count in the stagger but have nothing to draw."""
    n = len(text)
    if n == 0:
        return []
    span = overlap / (n - 1 + overlap)   # one letter's grow, as a share of the whole
    step = (1 - span) / max(1, n - 1)
    return [ease(vb.clamp01((p - i * step) / span)) if p > i * step else 0.0 for i in range(n)]


def draw_scale_in(cv, text, font, x, y, p, color, alpha=1.0, **kw):
    """Draw `text` scaling in letter by letter at progress `p` (0 -> 1) from
    its top-left (x, y). Each letter grows about its own centre in its final
    place, so the line never shifts. `kw` goes to `char_scales`. Returns the
    Box of the finished line."""
    xs, width = type_kit.advances(text, font)
    h = vb.text.line_height(font)
    ctx = cv.ctx
    for i, (ch, s) in enumerate(zip(text, char_scales(text, p, **kw))):
        if ch.isspace() or s <= 0.001:
            continue
        gw = vb.text.measure(ch, font)
        cx, cy = x + xs[i] + gw / 2, y + h / 2
        ctx.save()
        ctx.translate(cx, cy)
        ctx.scale(s, s)
        type_kit.glyphs(cv, ch, font, -gw / 2, -h / 2, color, alpha=alpha)
        ctx.restore()
    return vb.Box(x, y, width, h)


def draw(n, cv):
    f = demo.font(150, 800)
    text = 'MOTION'
    w, h = vb.text.block_size([text], f)
    box = draw_scale_in(cv, text, f, (demo.W - w) / 2, (demo.H - h) / 2, demo.phase(n, 0.4, 2.2), demo.INK)
    cv.mark('text', *box)


TECHNIQUE = Technique(
    id='character-scale-in',
    name='Character scale-in',
    family='typography',
    group='Per-unit reveals',
    aliases=('letter pop-in', 'scale stagger', 'per-letter scale in'),
    definition='The letters of a word show up one after another, each swelling from a point '
               'to full size in its own spot until the whole word stands there.',
    phrasings=('make each letter pop in one at a time',
               'grow the title in letter by letter from nothing',
               'the word scales up character by character, left to right'),
    related=('circle-pop', 'scale-zoom-through', 'center-out-stagger', 'text-to-shape-morph',
             'edge-in-stagger', 'letter-morph'),
    api=('videobuilder.techniques.typography.character_scale_in.draw_scale_in',
         'videobuilder.techniques.typography.character_scale_in.char_scales'),
    demo=lambda: demo.film(draw),
)
