"""Backspace Erase: a line of text loses its last letter, then the one before,
until nothing is left but the caret -- typing played backwards."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def erased(text, p, hold=0.0, speedup=0.6):
    """How many characters of `text` are still standing at progress `p`
    (0 -> 1): all of them until `hold`, none at 1. `speedup` (0 -> 1) makes
    the strokes come faster as they go, like a held backspace key repeating;
    0 is an even rate."""
    q = vb.clamp01((p - hold) / (1 - hold)) if hold < 1 else float(p >= 1)
    q = (1 - speedup) * q + speedup * q * q  # starts slow, quickens
    return len(text) - min(len(text), int(q * len(text) + 1e-9))


def draw_backspace(cv, text, font, x, y, p, color, caret=None, blink=None, caret_width=None, **kw):
    """Draw `text` being backspaced away at progress `p` from its top-left
    (x, y), with a bar caret in `caret` (default `color`) riding the end of
    what's left. `blink`: seconds into the film, to blink the caret once the
    line is empty or before it starts (None: always on). `kw` goes to
    `erased`. Returns the Box of the full line, so a layout can reserve it."""
    shown = text[:erased(text, p, **kw)]
    if shown:
        vb.text.draw(cv, [shown], font, x, y, color)
    lh = vb.text.line_height(font)
    cx = x + (vb.text.measure(shown, font) if shown else 0)
    idle = shown == text or not shown
    if blink is None or not idle or (blink % 1.0) < 0.55:
        cw = caret_width or max(3.0, font.size * 0.07)
        cv.rect(cx + font.size * 0.04, y + lh * 0.12, cw, lh * 0.76, caret or color)
    w, h = vb.text.block_size([text], font)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    f = demo.font(104, 800)
    text = 'FIRST DRAFT'
    w, h = vb.text.block_size([text], f)
    box = draw_backspace(cv, text, f, (demo.W - w) / 2, (demo.H - h) / 2, demo.phase(n, 0.6, 2.3),
                         demo.INK, caret=demo.ACCENT, blink=n / demo.FPS)
    cv.mark('text', *box)


TECHNIQUE = Technique(
    id='backspace-erase',
    name='Backspace erase',
    family='typography',
    group='Typewriter and terminal',
    aliases=('delete and retype', 'character erase', 'backspace delete'),
    definition='A caret sits at the end of a line and eats it letter by letter from the right, '
               'leaving the line blank and waiting for new words.',
    phrasings=('the text deletes itself one letter at a time like someone hitting backspace',
               'un-type the headline so it can be replaced',
               'the words get erased backwards with a blinking cursor'),
    related=('wipe-reveal', 'glitch-text', 'underline-wipe', 'per-character-fade-in', 'character-drop',
             'scanline-wipe'),
    api=('videobuilder.techniques.typography.backspace_erase.draw_backspace',
         'videobuilder.techniques.typography.backspace_erase.erased'),
    demo=lambda: demo.film(draw),
)
