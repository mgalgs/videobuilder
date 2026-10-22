"""Character drop: the letters of a line fall in one after another from above,
each landing on the baseline with a small settle, until the word is whole."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def character_drop(text, p, stagger=0.6, ease=vb.ease_out_back):
    """`text` at progress `p` (0 -> 1) as one `(char, k)` per character, `k`
    the eased progress of that character's fall: 0 still above, 1 resting on
    the line (an overshooting `ease` dips it briefly below). The first
    character starts at 0 and the last at `stagger`, so each falls for
    `1 - stagger`. Spaces count as slots, keeping the rhythm even."""
    n = len(text)
    fall = 1 - stagger
    out = []
    for i, ch in enumerate(text):
        start = stagger * i / (n - 1) if n > 1 else 0
        t = vb.clamp01((p - start) / fall) if fall > 0 else float(p >= start)
        out.append((ch, ease(t) if t > 0 else 0.0))
    return out


def draw_character_drop(cv, text, font, x, y, p, color, height=260, fade=0.35, **kw):
    """Draw `text` dropping in at progress `p` from its top-left (x, y): each
    character starts `height` px above its place and falls onto it, fading in
    over the first `fade` of its fall. Characters not yet falling are not
    drawn. `kw` goes to `character_drop`. Returns the Box of the finished line."""
    for i, (ch, k) in enumerate(character_drop(text, p, **kw)):
        if k <= 0 or ch.isspace():
            continue
        gx = x + vb.text.measure(text[:i], font)
        alpha = vb.clamp01(k / fade) if fade > 0 else 1.0
        vb.text.draw(cv, [ch], font, gx, y - height * (1 - k), color, alpha=alpha)
    w, h = vb.text.block_size([text], font)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    f = demo.font(120, 800)
    text = 'Hello there'
    w, h = vb.text.block_size([text], f)
    x, y = (demo.W - w) / 2, (demo.H - h) / 2 + 40
    demo.floor(cv, y + h + 14, color=demo.LINE)
    box = draw_character_drop(cv, text, f, x, y, demo.phase(n, 0.3, 2.4), demo.INK, height=380, stagger=0.7)
    cv.mark('text', *box)


TECHNIQUE = Technique(
    id='character-drop',
    name='Character drop',
    family='typography',
    group='Per-unit reveals',
    aliases=('letter drop', 'fall into place', 'dropping letters'),
    definition='The letters of a word come down from above one after another and land on the line, '
               'so the word builds up a character at a time.',
    phrasings=('make the title drop in one letter at a time',
               'letters fall from the top and land in place',
               'each character drops down onto the line in sequence'),
    related=('physics-letter-drop', 'falling-letter-rain', 'gravity-drop', 'letter-roll',
             'falling-glyph-rain-reveal', 'letter-sort-animation'),
    api=('videobuilder.techniques.typography.character_drop.draw_character_drop',
         'videobuilder.techniques.typography.character_drop.character_drop'),
    demo=lambda: demo.film(draw),
)
