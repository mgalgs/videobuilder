"""Letter Sort Animation: the letters of a word stand in a jumbled order,
then each one travels along a little arc to its own place until they spell
the word."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ...type import kit as type_kit


def shuffled(text, seed=0):
    """`text` with its non-space letters in a jumbled order (spaces keep their
    places), never the original order when the letters allow another. The
    same `seed` gives the same jumble."""
    slots = [i for i, ch in enumerate(text) if not ch.isspace()]
    letters = [text[i] for i in slots]
    rnd = random.Random(seed)
    order = letters[:]
    for _ in range(50):
        rnd.shuffle(order)
        if order != letters:
            break
    out = list(text)
    for i, ch in zip(slots, order):
        out[i] = ch
    return ''.join(out)


def _sources(text, scrambled):
    """For each character of `text`, the index in `scrambled` it starts from:
    equal letters are matched first to first, so twin letters don't cross."""
    if sorted(text) != sorted(scrambled):
        raise ValueError(f'{scrambled!r} is not a reordering of {text!r}')
    free = {}
    for j, ch in enumerate(scrambled):
        free.setdefault(ch, []).append(j)
    return [free[ch].pop(0) for ch in text]


def letter_sort(text, font, p, scrambled=None, seed=0, stagger=0.5, lift=0.6, tilt=14.0):
    """Where each letter of `text` stands at progress `p` (0 -> 1) as it sorts
    from `scrambled` (default `shuffled(text, seed)`) into order: a list of
    `(char, x, dy, angle)`, `x` the letter's left edge from the line's start,
    `dy` its lift off the baseline (negative is up) and `angle` its tilt in
    degrees. Letters set off one after another across the first `stagger` of
    the move, each easing along an arc `lift` line-heights tall (alternately
    over and under the line) and tilting up to `tilt` degrees mid-flight.
    Letters already in place stay put."""
    scrambled = shuffled(text, seed) if scrambled is None else scrambled
    src = _sources(text, scrambled)
    xs_to, _ = type_kit.advances(text, font)
    xs_from, _ = type_kit.advances(scrambled, font)
    lh = vb.text.line_height(font)
    moving = [i for i in range(len(text)) if xs_from[src[i]] != xs_to[i]]
    out = []
    for i, ch in enumerate(text):
        a, b = xs_from[src[i]], xs_to[i]
        if i not in moving:
            out.append((ch, b, 0.0, 0.0))
            continue
        k = moving.index(i)
        start = stagger * k / max(1, len(moving) - 1)
        t = vb.clamp01((p - start) / (1 - stagger))
        q = vb.ease_in_out_quart(t)
        side = -1 if k % 2 == 0 else 1
        hop = math.sin(math.pi * q) if 0 < t < 1 else 0.0   # exactly on the line at rest
        reach = min(1.0, abs(b - a) / (4 * lh) + 0.4)   # short hops arc less than long ones
        out.append((ch, a + (b - a) * q, side * lift * lh * reach * hop, side * tilt * hop))
    return out


def draw_letter_sort(cv, text, font, x, y, p, color, moving=None, **kw):
    """Draw `text` sorting itself at progress `p` from its top-left (x, y);
    letters in flight are drawn in `moving` (default `color`). `kw` goes to
    `letter_sort`. Returns the Box of the finished line."""
    lh = vb.text.line_height(font)
    for ch, lx, dy, angle in letter_sort(text, font, p, **kw):
        if ch.isspace():
            continue
        gw = vb.text.measure(ch, font)
        ctx = cv.ctx
        ctx.save()
        ctx.translate(x + lx + gw / 2, y + dy + lh / 2)
        ctx.rotate(math.radians(angle))
        type_kit.glyphs(cv, ch, font, -gw / 2, -lh / 2, moving if (moving and dy) else color)
        ctx.restore()
    w, h = vb.text.block_size([text], font)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    f = demo.font(150, 800)
    text = 'SORTED'
    w, h = vb.text.block_size([text], f)
    box = draw_letter_sort(cv, text, f, (demo.W - w) / 2, (demo.H - h) / 2, demo.phase(n, 0.5, 2.5),
                           demo.INK, moving=demo.ACCENT, scrambled='DTOESR')
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='letter-sort-animation',
    name='Letter sort animation',
    family='typography',
    group='Wave and motion',
    aliases=('alphabetize shuffle', 'letter reorder', 'anagram sort'),
    definition='A word starts with its letters in the wrong order, and each letter glides along '
               'a small arc to its proper spot until the word reads correctly.',
    phrasings=('the jumbled letters rearrange themselves into the word',
               'start with an anagram and have the letters swap places to spell the title',
               'letters shuffle around and settle into the right order'),
    related=('letter-roll', 'grid-reflow-shuffle', 'random-order-character-reveal', 'character-slide-in',
             'pixel-sort-text', 'character-rotate-in'),
    api=('videobuilder.capabilities.typography.letter_sort_animation.draw_letter_sort',
         'videobuilder.capabilities.typography.letter_sort_animation.letter_sort',
         'videobuilder.capabilities.typography.letter_sort_animation.shuffled'),
    demo=lambda: demo.film(draw),
)
