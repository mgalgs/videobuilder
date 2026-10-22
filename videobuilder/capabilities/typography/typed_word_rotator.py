"""Typed word rotator: a fixed lead-in stays put while the word after it is
typed in, held with a blinking caret, backspaced away, and replaced by the
next word in the list."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ...type.typewriter import schedule


def _cycle(word, i, type_per_char, hold, delete_per_char, gap):
    """One word's keystroke times (from its own start), and when its hold,
    its deleting and its whole cycle end."""
    keys, span = schedule(word, f'rotator:{i}:{word}', type_per_char)
    held = span + hold
    deleted = held + len(word) * delete_per_char
    return keys, span, held, deleted, deleted + gap


def rotate_typed(words, t, type_per_char=0.065, hold=0.45, delete_per_char=0.03, gap=0.1, loop=False):
    """What the rotator shows `t` seconds in: `(index, shown, state)`, where
    `shown` is how many letters of `words[index]` are on screen and `state`
    is 'typing', 'holding' or 'deleting'. Each word types in with a slightly
    uneven cadence, holds for `hold` seconds, deletes one letter every
    `delete_per_char` seconds, then waits `gap` before the next. Without
    `loop` the last word is typed and then held for good; with it the list
    starts over."""
    if t < 0:
        return 0, 0, 'typing'
    cycles = [_cycle(w, i, type_per_char, hold, delete_per_char, gap) for i, w in enumerate(words)]
    if loop:
        t %= sum(c[4] for c in cycles)
    for i, (word, (keys, span, held, deleted, end)) in enumerate(zip(words, cycles)):
        last = i == len(words) - 1 and not loop
        if t < span or (last and t < end):
            n = sum(1 for k in keys if k <= t)
            return i, n, 'typing' if n < len(word) else 'holding'
        if t < held or last:
            return i, len(word), 'holding'
        if t < end:
            gone = min(len(word), int((t - held) / delete_per_char) + 1)
            return i, len(word) - gone, 'deleting'
        t -= end
    return len(words) - 1, len(words[-1]), 'holding'


def draw_typed_rotator(cv, lead, words, font, x, y, t, color, word_color=None, caret_color=None,
                       blink=0.9, **kw):
    """Draw `lead` then the rotating word at `t` seconds, from the line's
    top-left (x, y). The lead never moves; the word after it types and
    deletes, a caret riding its end, solid while keys are moving and
    blinking (period `blink` seconds) while a word holds. `word_color` and
    `caret_color` default to `color`; `kw` goes to `rotate_typed`. Returns
    the Box of the lead plus the longest word."""
    i, shown, state = rotate_typed(words, t, **kw)
    lead_w = vb.text.measure(lead, font) if lead else 0.0
    if lead:
        vb.text.draw(cv, [lead], font, x, y, color)
    part = words[i][:shown]
    if part:
        vb.text.draw(cv, [part], font, x + lead_w, y, word_color or color)
    lh = vb.text.line_height(font)
    if state != 'holding' or (t % blink) < blink * 0.55:
        cx = x + lead_w + (vb.text.measure(part, font) if part else 0.0) + font.size * 0.04
        cv.rect(cx, y + lh * 0.12, max(2.0, font.size * 0.07), lh * 0.76, caret_color or word_color or color)
    w = lead_w + max(vb.text.measure(wd, font) for wd in words)
    return vb.Box(x, y, w, lh)


LEAD = 'We make '
WORDS = ('films', 'apps', 'brands')


def draw(n, cv):
    f = demo.font(104, 800)
    w = vb.text.measure(LEAD, f) + max(vb.text.measure(wd, f) for wd in WORDS)
    h = vb.text.line_height(f)
    box = draw_typed_rotator(cv, LEAD, WORDS, f, (demo.W - w) / 2, (demo.H - h) / 2, n / demo.FPS - 0.2,
                             demo.INK, word_color=demo.ACCENT, caret_color=demo.TEAL)
    cv.mark('text', *box)


TECHNIQUE = Technique(
    id='typed-word-rotator',
    name='Typed word rotator',
    family='typography',
    group='Typewriter and terminal',
    aliases=('typing carousel', 'typewriter word swap', 'rotating typed text', 'typed text loop'),
    definition='A short phrase stays fixed while its last word is typed out, backspaced away and typed '
               'again as a different word, a caret blinking at the end of the line.',
    phrasings=('the end of the sentence keeps typing and deleting itself to show different words',
               'type one word, erase it, then type the next one after the same opening words',
               'a headline where the final word cycles through options like someone is typing them'),
    related=('word-carousel-rotate', 'headline-rotator', 'word-flip-in', 'twirl-warp-text',
             'scroll-driven-text-reveal', 'letter-roll'),
    api=('videobuilder.techniques.typography.typed_word_rotator.draw_typed_rotator',
         'videobuilder.techniques.typography.typed_word_rotator.rotate_typed'),
    demo=lambda: demo.film(draw),
)
