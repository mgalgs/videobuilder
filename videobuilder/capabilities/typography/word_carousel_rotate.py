"""Word Carousel Rotate: one word in a line is a slot that keeps changing --
the current word rolls up and out of a clipped window while the next rises
into it from below, looping through a list."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def carousel(words, t, hold=0.6, swap=0.35, ease=vb.ease_in_out_quart):
    """Where a word carousel is `t` seconds in: `(out, into, p)`, the indices
    of the leaving and arriving words and the eased swap progress 0 -> 1.
    Each word holds for `hold` seconds, then takes `swap` seconds to give way
    to the next; after the last word the list starts again. While a word
    holds, `out == into` and `p` is 0."""
    period = hold + swap
    k, u = divmod(max(0.0, t), period)
    out = int(k) % len(words)
    if u < hold:
        return out, out, 0.0
    return out, (out + 1) % len(words), ease((u - hold) / swap)


def draw_carousel(cv, words, font, x, y, t, color, hold=0.6, swap=0.35, ease=vb.ease_in_out_quart,
                  travel=1.0, fade=True):
    """Draw the word slot of a carousel `t` seconds in, from its top-left
    (x, y). The leaving word slides up and the arriving one slides up from
    below, both clipped to one line so neither shows outside the slot; they
    move `travel` line heights. With `fade`, each fades as it crosses the
    edge. Returns the Box of the slot at its current width, which eases
    between the two words' widths, so text after it can follow along."""
    out, into, p = carousel(words, t, hold, swap, ease)
    lh = vb.text.line_height(font)
    w0, w1 = vb.text.measure(words[out], font), vb.text.measure(words[into], font)
    pad = lh * 0.25  # room for descenders and accents above the cap height
    with cv.clip(x - pad, y - pad, max(w0, w1) + 2 * pad, lh + 2 * pad):
        d = lh * travel
        if p <= 0:
            vb.text.draw(cv, [words[out]], font, x, y, color)
        else:
            vb.text.draw(cv, [words[out]], font, x, y - d * p, color, alpha=1 - p if fade else 1.0)
            vb.text.draw(cv, [words[into]], font, x, y + d * (1 - p), color, alpha=p if fade else 1.0)
    return vb.Box(x, y, w0 + (w1 - w0) * p, lh)


# An odd number of words, so the clip's middle frame (the gallery poster) lands half a period after its
# first: the clip opens on a word holding and the poster catches a swap.
WORDS = ('MOTION', 'RHYTHM', 'ENERGY', 'COLOUR', 'LIGHT')
HOLD, SWAP = 0.55, 0.35
# Exactly one trip round the list, so the clip's last frame runs straight on into its first.
SECONDS = len(WORDS) * (HOLD + SWAP)
START = 0.28  # seconds into the carousel the clip begins, part-way through MOTION's hold


def draw(n, cv):
    f = demo.font(84, 800)
    lead = 'MADE OF '
    t = n / demo.FPS + START
    h = vb.text.line_height(f)
    lw = vb.text.measure(lead, f)
    # Centre the whole phrase on the slot's current width, so the line re-centres smoothly at each swap.
    out, into, p = carousel(WORDS, t, HOLD, SWAP)
    ww = vb.text.measure(WORDS[out], f) * (1 - p) + vb.text.measure(WORDS[into], f) * p
    x = (demo.W - lw - ww) / 2
    y = (demo.H - h) / 2
    vb.text.draw(cv, [lead], f, x, y, demo.INK)
    box = draw_carousel(cv, WORDS, f, x + lw, y, t, demo.ACCENT, HOLD, SWAP)
    cv.mark('word', *box)


CAPABILITY = Capability(
    id='word-carousel-rotate',
    name='Word carousel rotate',
    family='typography',
    group='Looping and marquee',
    aliases=('text rotator', 'swap word carousel', 'rotating word', 'word roller'),
    definition='One word in a fixed line keeps changing: it rolls up out of view while the next word '
               'rises into its place from below, looping through a list.',
    phrasings=('the last word of the headline keeps swapping between a few options',
               'a sentence where one word rolls up and gets replaced, over and over',
               'rotate through several words in the same spot'),
    related=('word-flip-in', 'typed-word-rotator', 'carousel-slide', 'headline-rotator', 'twirl-warp-text',
             'character-slide-in'),
    api=('videobuilder.capabilities.typography.word_carousel_rotate.draw_carousel',
         'videobuilder.capabilities.typography.word_carousel_rotate.carousel'),
    demo=lambda: demo.film(draw, SECONDS),
)
