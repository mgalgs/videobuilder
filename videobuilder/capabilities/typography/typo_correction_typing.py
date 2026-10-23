"""Typo-correction typing: a line types itself in, but at a chosen spot the
wrong letters go in, the caret waits a beat, backspaces over them and the
right letters follow."""
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def keystrokes(text, typos, per_char=0.1, pause=0.45, seed=0):
    """The keystroke script for typing `text` with mistakes, as `(time, shown)`
    pairs from 0: `shown` is the line right after that key. `typos` maps an
    index of `text` to the wrong letters typed there instead; after them the
    typist stops for `pause`, backspaces them one by one (quicker than typing)
    and goes on with the right letter. Key gaps are a little uneven, longer
    after a space; the same `seed` gives the same rhythm."""
    rnd = random.Random(seed)
    t, shown, out = 0.0, '', []

    def key(s, gap):
        nonlocal t, shown
        shown = s
        out.append((t, s))
        t += gap

    for i, ch in enumerate(text):
        for wrong in typos.get(i, ''):
            key(shown + wrong, per_char * rnd.uniform(0.7, 1.2))
        if typos.get(i):
            t += pause
            for _ in typos[i]:
                key(shown[:-1], per_char * 0.55)
            t += per_char * 0.6
        key(shown + ch, per_char * rnd.uniform(0.55, 1.45) * (1.8 if ch == ' ' else 1.0))
    return out


def typed_at(text, typos, t, **kw):
    """The line at time `t` (seconds from the first key) as `(shown, wrong)`:
    what is on screen, and how many of its last letters are the typo not yet
    deleted. `kw` goes to `keystrokes`."""
    shown = ''
    for k, s in keystrokes(text, typos, **kw):
        if k > t:
            break
        shown = s
    good = 0
    while good < len(shown) and good < len(text) and shown[good] == text[good]:
        good += 1
    return shown, len(shown) - good


def draw_typo_typing(cv, text, typos, font, x, y, t, color, wrong_color=None, caret=None, **kw):
    """Draw `text` being typed with corrections at time `t` from its top-left
    (x, y), with a caret after the last letter. Letters still to be
    deleted are drawn in `wrong_color` (default: `color`); the caret, in
    `caret` (default: `color`), blinks once typing is done. `kw` goes to
    `keystrokes`. Returns the Box of the finished line."""
    shown, wrong = typed_at(text, typos, t, **kw)
    good = shown[:len(shown) - wrong]
    if good:
        vb.text.draw(cv, [good], font, x, y, color)
    if wrong:
        vb.text.draw(cv, [shown[len(good):]], font, x + vb.text.measure(good, font), y, wrong_color or color)
    end = keystrokes(text, typos, **kw)[-1][0]
    w, h = vb.text.block_size([text], font)
    if t < end + 0.1 or (t - end) % 1.0 < 0.55:
        cx = x + (vb.text.measure(shown, font) if shown else 0) + font.size * 0.04
        cv.rect(cx, y + h * 0.1, max(2.0, font.size * 0.05), h * 0.8, caret or color)
    return vb.Box(x, y, w, h)


TEXT, TYPOS = 'MOTION DESIGN', {10: 'GI'}   # DESGI, then back to DES and on


def draw(n, cv):
    # Timed so the red GI and the waiting caret are on screen from 1.34s to 2.32s, across the
    # poster at 2.1s, and the fixed line still holds from 2.64s; at 88px it keeps ~110px each side.
    f = demo.font(88, 800)
    w, h = vb.text.block_size([TEXT], f)
    box = draw_typo_typing(cv, TEXT, TYPOS, f, (demo.W - w) / 2, (demo.H - h) / 2, n / demo.FPS - 0.5,
                           demo.INK, wrong_color=demo.ACCENT, caret=demo.TEAL, per_char=0.08, pause=0.9, seed=3)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='typo-correction-typing',
    name='Typo-correction typing',
    family='typography',
    group='Typewriter and terminal',
    aliases=('mistype and fix', 'human typing simulation', 'typing with backspace'),
    definition='Text types itself in but hits a wrong letter, hesitates, backspaces over it and '
               'carries on with the right one, like a person fixing a slip.',
    phrasings=('the title types out with a typo that gets deleted and fixed',
               'make it look like someone mistyped and hit backspace',
               'typing animation where it gets a letter wrong and corrects it'),
    related=('glitch-text', 'error-shake', 'emoji-substitution', 'symbol-to-letter-decode', 'stutter-cut',
             'character-slide-in'),
    api=('videobuilder.capabilities.typography.typo_correction_typing.draw_typo_typing',
         'videobuilder.capabilities.typography.typo_correction_typing.keystrokes',
         'videobuilder.capabilities.typography.typo_correction_typing.typed_at'),
    demo=lambda: demo.film(draw),
)
