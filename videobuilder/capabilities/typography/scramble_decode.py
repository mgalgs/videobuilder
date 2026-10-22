"""Scramble Decode: every character flickers through random glyphs, then the
real letters lock in one by one from left to right."""
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

GLYPHS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#%&*+=<>/?'


def scramble(text, p, seed=0, glyphs=GLYPHS, changes=30, lead=0.25):
    """`text` at progress `p` (0 -> 1) as `(char, settled)` pairs. The first
    character settles just after `lead`, the last at 1; until then each shows
    a random glyph, re-drawn `changes` times across the reveal. Spaces stay
    spaces. The same `seed` gives the same glyphs, frame for frame."""
    step = int(vb.clamp01(p) * changes)
    out = []
    for i, ch in enumerate(text):
        settled = ch.isspace() or p >= lead + (1 - lead) * (i + 1) / len(text)
        out.append((ch, True) if settled else (random.Random(f'{seed}:{i}:{step}').choice(glyphs), False))
    return out


def draw_scramble(cv, text, font, x, y, p, color, scrambled=None, seed=0, **kw):
    """Draw `text` decoding at progress `p` from its top-left (x, y), each
    glyph centred on its real letter's place so the line never jitters.
    Unsettled glyphs use `scrambled` (default: `color` at half strength).
    `kw` goes to `scramble`. Returns the Box of the finished line."""
    left = x
    for (glyph, settled), ch in zip(scramble(text, p, seed=seed, **kw), text):
        adv = vb.text.measure(ch, font)
        gx = left + (adv - vb.text.measure(glyph, font)) / 2
        if settled:
            vb.text.draw(cv, [glyph], font, gx, y, color)
        else:
            vb.text.draw(cv, [glyph], font, gx, y, scrambled or color, alpha=1.0 if scrambled else 0.5)
        left += adv
    w, h = vb.text.block_size([text], font)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    f = demo.mono(68, 700)
    text = 'SIGNAL ACQUIRED'
    w, h = vb.text.block_size([text], f)
    box = draw_scramble(cv, text, f, (demo.W - w) / 2, (demo.H - h) / 2, demo.phase(n, 0.3, 2.3),
                        demo.INK, scrambled=demo.TEAL, seed=7)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='scramble-decode',
    name='Scramble Decode',
    family='typography',
    group='Scramble and decode',
    aliases=('text scramble', 'decode text', 'hacker text'),
    definition='Each letter flickers through random characters before locking onto the real one, '
               'the line resolving from left to right.',
    phrasings=('the text scrambles and then decodes into the words',
               'letters cycle like a code being cracked until the title appears',
               'random characters that resolve into the headline'),
    related=('typewriter', 'split-flap', 'glitch-text'),
    api=('videobuilder.capabilities.typography.scramble_decode.draw_scramble',
         'videobuilder.capabilities.typography.scramble_decode.scramble'),
    demo=lambda: demo.film(draw),
)
