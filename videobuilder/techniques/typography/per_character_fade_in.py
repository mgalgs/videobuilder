"""Per-character Fade-in: a line of text appears one letter at a time, each
letter fading up from nothing a moment after the one before it."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def char_alphas(text, p, overlap=0.85, ease=vb.linear):
    """Opacity of each character of `text` at progress `p` (0 -> 1). Each
    letter's own fade starts a step after the last; `overlap` (0 -> 1) is how
    much the fades run over each other (0: strictly one after another, near 1:
    a soft wave across the line). The first starts at 0, the last ends at 1."""
    n = len(text)
    if n == 0:
        return []
    span = 1 / (n - (n - 1) * overlap)       # each letter's own fade length, as a share of the whole
    step = span * (1 - overlap)
    return [ease(vb.clamp01((p - i * step) / span)) for i in range(n)]


def draw_fade_in(cv, text, font, x, y, p, color, rise=0.0, **kw):
    """Draw `text` from its top-left (x, y) with its letters fading in one
    after another at progress `p`. Each letter sits where it would in the
    whole line (kerning kept), and drops the last `rise` px into place as it
    fades. `kw` goes to `char_alphas`. Returns the Box of the finished line."""
    for i, (ch, a) in enumerate(zip(text, char_alphas(text, p, **kw))):
        if a <= 0 or ch.isspace():
            continue
        vb.text.draw(cv, [ch], font, x + vb.text.measure(text[:i], font), y + rise * (1 - a), color, alpha=a)
    w, h = vb.text.block_size([text], font)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    f = demo.font(110, 800)
    text = 'Quietly arriving'
    w, h = vb.text.block_size([text], f)
    box = draw_fade_in(cv, text, f, (demo.W - w) / 2, (demo.H - h) / 2, demo.phase(n, 0.3, 2.4), demo.INK,
                       overlap=0.85)
    cv.mark('text', *box)


TECHNIQUE = Technique(
    id='per-character-fade-in',
    name='Per-character fade-in',
    family='typography',
    group='Per-unit reveals',
    aliases=('letter-by-letter fade', 'character fade', 'staggered letter fade'),
    definition='A line of text fades in one letter at a time from left to right, each letter '
               'starting to appear just after the one before it.',
    phrasings=('fade the title in letter by letter',
               'have each character softly appear one after another',
               'the words gently fade on a letter at a time'),
    related=('outline-pulse-glow', 'ascii-art-render', 'text-mask-reveal', 'letter-morph', 'pixel-sort-text',
             'text-on-a-path'),
    api=('videobuilder.techniques.typography.per_character_fade_in.draw_fade_in',
         'videobuilder.techniques.typography.per_character_fade_in.char_alphas'),
    demo=lambda: demo.film(draw),
)
