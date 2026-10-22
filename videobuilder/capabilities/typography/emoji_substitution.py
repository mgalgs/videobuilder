"""Emoji Substitution: chosen letters in a word pop out and an emoji pops
into each one's place, so the word still reads with the picture standing in
for a letter (the O of LOVE becoming a heart).

Emoji draw through Pango's font fallback, so they need a colour emoji font
installed (the release image ships Noto Color Emoji)."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def swap_scales(p):
    """At progress `p` (0 -> 1) of one swap, the `(letter, emoji)` scales:
    the letter shrinks away over the first 40%, then the emoji springs in
    with a small overshoot over the rest."""
    out = vb.clamp01(p / 0.4)
    letter = 1 - vb.ease_in_expo(out) if p < 0.4 else 0.0
    emoji = vb.ease_out_back(vb.clamp01((p - 0.4) / 0.6)) if p > 0.4 else 0.0
    return letter, emoji


def draw_emoji_swap(cv, text, swaps, font, x, y, p, color, stagger=0.25, emoji_scale=1.0):
    """Draw `text` from its top-left (x, y) with the letters at the indices
    in `swaps` (`{index: emoji}`) turning into their emoji as `p` runs 0 -> 1.
    The swaps go in index order, each starting `stagger` of the way after the
    one before; each emoji is centred on the place of the letter it replaces,
    so the rest of the line never moves. `emoji_scale` sizes the emoji
    against the font. Returns the Box of the line."""
    order = sorted(swaps)
    span = 1 - stagger * (len(order) - 1) if order else 1
    if span <= 0:
        raise ValueError(f'stagger {stagger} is too long for {len(order)} swaps')
    w, h = vb.text.block_size([text], font)
    efont = vb.Font(font.family, font.size * emoji_scale, weight=font.weight)
    eh = vb.text.block_size(['M'], efont)[1]
    left = x
    for i, ch in enumerate(text):
        adv = vb.text.measure(ch, font)
        if i not in swaps:
            vb.text.draw(cv, [ch], font, left, y, color)
        else:
            k = order.index(i)
            letter, emoji = swap_scales(vb.clamp01((p - stagger * k) / span))
            cx, cy = left + adv / 2, y + h / 2
            if letter > 0:
                with cv.layer(dx=cx, dy=cy, scale=letter):
                    vb.text.draw(cv, [ch], font, -adv / 2, -h / 2, color)
            if emoji > 0:
                glyph = swaps[i]
                ew = vb.text.measure(glyph, efont)
                with cv.layer(dx=cx, dy=cy, scale=emoji):
                    vb.text.draw(cv, [glyph], efont, -ew / 2, -eh / 2, color)
        left += adv
    return vb.Box(x, y, w, h)


def draw(n, cv):
    f = demo.font(104, 900)
    text = 'GOOD MORNING'
    w, h = vb.text.block_size([text], f)
    box = draw_emoji_swap(cv, text, {1: '☀️', 2: '☕'}, f, (demo.W - w) / 2, (demo.H - h) / 2,
                          demo.phase(n, 0.6, 2.2), demo.INK, stagger=0.35, emoji_scale=0.72)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='emoji-substitution',
    name='Emoji substitution',
    family='typography',
    group='Glyph swaps',
    aliases=('emoji letter swap', 'emoji in place of a letter', 'emoji replacement'),
    definition='A letter in a word shrinks away and an emoji pops up in its exact spot, '
               'so the word still reads with a picture standing in for that letter.',
    phrasings=('swap the O in the word for a little heart emoji',
               'have some of the letters turn into emojis',
               'replace a letter with an emoji that pops in'),
    related=('word-carousel-rotate', 'text-to-shape-morph', 'floating-reaction-emoji', 'character-slide-in',
             'letter-sort-animation', 'hover-letter-displacement'),
    api=('videobuilder.capabilities.typography.emoji_substitution.draw_emoji_swap',
         'videobuilder.capabilities.typography.emoji_substitution.swap_scales'),
    demo=lambda: demo.film(draw),
)
