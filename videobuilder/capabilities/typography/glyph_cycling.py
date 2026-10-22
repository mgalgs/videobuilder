"""Glyph Cycling: each letter steps through its alphabet in order -- A, B,
C, ... -- running one full lap and landing back on itself, the laps
staggered across the word so the cycling rolls through it."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

SETS = ('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz', '0123456789')


def cycle_char(ch, steps, sets=SETS):
    """`ch` moved `steps` places along whichever of `sets` holds it, wrapping
    round; a character in none of them comes back unchanged."""
    for s in sets:
        i = s.find(ch)
        if i >= 0:
            return s[(i + steps) % len(s)]
    return ch


def glyph_cycle(text, p, laps=1, spread=0.6, sets=SETS):
    """`text` at progress `p` (0 -> 1) as `(char, cycling)` pairs. Each
    character runs `laps` full trips round its set, in order, and lands back
    on itself; the first starts at 0, the last finishes at 1, and `spread`
    (0 -> 1) is how much of the run the starts are staggered over. Characters
    outside `sets` (spaces, punctuation) never move."""
    n = max(1, len(text) - 1)
    out = []
    for i, ch in enumerate(text):
        size = next((len(s) for s in sets if ch in s), 0)
        start = spread * i / n
        t = vb.clamp01((p - start) / (1 - spread)) if spread < 1 else float(p >= start)
        steps = int(t * laps * size)
        moving = 0 < t < 1 and size > 0
        out.append((cycle_char(ch, steps, sets) if moving else ch, moving))
    return out


def draw_glyph_cycle(cv, text, font, x, y, p, color, cycling=None, **kw):
    """Draw `text` cycling at progress `p` from its top-left (x, y), each
    glyph centred on its real letter's place so the line holds still. Letters
    mid-cycle use `cycling` (default `color`). `kw` goes to `glyph_cycle`.
    Returns the Box of the line."""
    left = x
    for (glyph, moving), ch in zip(glyph_cycle(text, p, **kw), text):
        adv = vb.text.measure(ch, font)
        gx = left + (adv - vb.text.measure(glyph, font)) / 2
        vb.text.draw(cv, [glyph], font, gx, y, (cycling or color) if moving else color)
        left += adv
    w, h = vb.text.block_size([text], font)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    f = demo.mono(150, 800)
    text = 'GLYPHS'
    w, h = vb.text.block_size([text], f)
    box = draw_glyph_cycle(cv, text, f, (demo.W - w) / 2, (demo.H - h) / 2, demo.phase(n, 0.4, 2.6),
                           demo.INK, cycling=demo.ACCENT, spread=0.55)
    cv.mark('text', *box)


TECHNIQUE = Technique(
    id='glyph-cycling',
    name='Glyph cycling',
    family='typography',
    group='Glyph swaps',
    aliases=('character cycling', 'character offset', 'letter cycling', 'alphabet roll'),
    definition='Each letter of a word ticks through the alphabet in order and comes back round to itself, '
               'the cycling rolling across the word one letter after another.',
    phrasings=('make the letters run through the alphabet and land back on the word',
               'each character flips through A to Z in sequence, one after the next',
               'the letters cycle through other characters like a counter before settling'),
    related=('character-rotate-in', 'letter-morph', 'hue-cycle-fill', 'letter-sort-animation',
             'typeface-crossfade', 'scramble-decode'),
    api=('videobuilder.techniques.typography.glyph_cycling.draw_glyph_cycle',
         'videobuilder.techniques.typography.glyph_cycling.glyph_cycle',
         'videobuilder.techniques.typography.glyph_cycling.cycle_char'),
    demo=lambda: demo.film(draw),
)
