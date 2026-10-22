"""Random-order character reveal: the letters of a line appear one at a time
in a shuffled order, each in its final place, until the whole line is there."""
import random

import videobuilder as vb
from videobuilder.type import kit as type_kit

from .. import _demo as demo
from ..schema import Capability


def reveal_order(text, seed=0):
    """The indices of `text`'s non-space characters in the shuffled order they
    appear. The same `seed` gives the same order."""
    order = [i for i, ch in enumerate(text) if not ch.isspace()]
    random.Random(f'reveal:{seed}').shuffle(order)
    return order


def random_reveal(text, p, seed=0, fade=0.15):
    """Each character's own progress (0 -> 1) at overall progress `p`, in
    text order. Characters start in `reveal_order`, evenly spread so the last
    finishes at `p` = 1, each taking `fade` of the reveal to arrive. Spaces
    are always 1."""
    order = reveal_order(text, seed)
    out = [1.0] * len(text)
    span = 1 - fade
    for k, i in enumerate(order):
        start = span * k / max(1, len(order) - 1)
        out[i] = vb.clamp01((p - start) / fade) if fade > 0 else float(p >= start)
    return out


def draw_random_reveal(cv, text, font, x, y, p, color, flash=None, seed=0, fade=0.15, rise=0.12):
    """Draw `text` revealing in random order at progress `p` from its top-left
    (x, y). Each letter fades up in its kerned place, dropping in from
    `rise` x its height above; with `flash`, it arrives in that colour and
    settles to `color`. Returns the Box of the finished line."""
    xs, width = type_kit.advances(text, font)
    h = vb.text.line_height(font)
    for ch, cx, q in zip(text, xs, random_reveal(text, p, seed=seed, fade=fade)):
        if q <= 0 or ch.isspace():
            continue
        e = vb.ease_out_expo(q)
        ink = type_kit.mix(flash, color, e) if flash else color
        vb.text.draw(cv, [ch], font, x + cx, y - rise * h * (1 - e), ink, alpha=e)
    return vb.Box(x, y, width, h)


def draw(n, cv):
    f = demo.font(120, 800)
    text = 'SHUFFLED IN'
    w, h = vb.text.block_size([text], f)
    box = draw_random_reveal(cv, text, f, (demo.W - w) / 2, (demo.H - h) / 2, demo.phase(n, 0.3, 2.3),
                             demo.INK, flash=demo.ACCENT, seed=3, fade=0.12)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='random-order-character-reveal',
    name='Random-order character reveal',
    family='typography',
    group='Per-unit reveals',
    aliases=('random letter reveal', 'shuffled character reveal', 'random stagger text'),
    definition='The letters of a word pop into their final places one by one in a shuffled order, '
               'so the text fills in patchily rather than left to right.',
    phrasings=('make the letters of the title appear one at a time in a random order',
               'the word fills in letter by letter, but scattered instead of left to right',
               'characters blink on randomly until the whole headline is there'),
    related=('scramble-decode', 'letter-sort-animation', 'random-stagger', 'text-mask-reveal',
             'typewriter-reveal', 'dither-reveal'),
    api=('videobuilder.capabilities.typography.random_order_character_reveal.draw_random_reveal',
         'videobuilder.capabilities.typography.random_order_character_reveal.random_reveal',
         'videobuilder.capabilities.typography.random_order_character_reveal.reveal_order'),
    demo=lambda: demo.film(draw),
)
