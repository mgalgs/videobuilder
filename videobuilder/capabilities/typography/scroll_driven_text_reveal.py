"""Scroll-driven text reveal: a dimmed paragraph fills in word by word as the
page scrolls, and un-fills when it scrolls back -- the scroll position, not
time, drives the reveal."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def scroll_fill(count, scroll, soft=1.5):
    """How filled each of `count` words is (0 -> 1) at `scroll` (0 -> 1).
    The fill front sweeps from before the first word to past the last, each
    word blending in over `soft` words' worth of scroll, so the same `scroll`
    always gives the same fill whichever way it is moving."""
    front = vb.clamp01(scroll) * (count + soft)
    return [vb.clamp01((front - i) / soft) for i in range(count)]


def draw_scroll_text(cv, lines, font, x, y, scroll, color, dim, soft=1.5):
    """Draw `lines` top-down from (x, y) in `dim`, each word filling to
    `color` from left to right as `scroll` (0 -> 1) passes it; `soft` is as
    in `scroll_fill`. A film drives `scroll` from its own scroll position.
    Returns the Box of the block."""
    if isinstance(lines, str):
        lines = [lines]
    lh = vb.text.line_height(font)
    words = []  # (word, left, top)
    for row, line in enumerate(lines):
        left = x
        for w in line.split():
            words.append((w, left, y + row * lh))
            left += vb.text.measure(w + ' ', font)
    for (w, left, top), f in zip(words, scroll_fill(len(words), scroll, soft)):
        vb.text.draw(cv, [w], font, left, top, dim)
        if f > 0:
            ww = vb.text.measure(w, font)
            with cv.clip(left, top, ww * f, lh):
                vb.text.draw(cv, [w], font, left, top, color)
    bw, bh = vb.text.block_size(lines, font)
    return vb.Box(x, y, bw, bh)


TEXT = ('Scroll down and the words light up one after another. '
        'Scroll back up and they fade out again.')
DIM = '#3a3d46'  # the unread words: visible, but well behind the read ones
TRACK_X, TRACK_TOP, TRACK_H, THUMB_H = demo.W - 70, 90, demo.H - 180, 64


def scroll_at(n):
    """The demo's scroll position: down most of the way, back up a little, then to the end."""
    down = vb.ease_in_out_quart(demo.phase(n, 0.2, 1.5)) * 0.8
    back = vb.ease_in_out_quart(demo.phase(n, 1.6, 2.0)) * 0.25
    on = vb.ease_in_out_quart(demo.phase(n, 2.1, 2.8)) * 0.45
    return down - back + on


def draw(n, cv):
    s = scroll_at(n)
    f = demo.font(40, 800)
    lines = vb.text.wrap(TEXT, f, demo.W - 300)
    bw, bh = vb.text.block_size(lines, f)
    x = (demo.W - 70 - bw) / 2
    y = (demo.H - bh) / 2 + 40 - 80 * s  # the page drifts up as it scrolls
    box = draw_scroll_text(cv, lines, f, x, y, s, demo.INK, DIM)
    cv.mark('text', *box)
    cv.rect(TRACK_X, TRACK_TOP, 4, TRACK_H, demo.LINE, radius=3)
    cv.rect(TRACK_X - 2, TRACK_TOP + (TRACK_H - THUMB_H) * s, 8, THUMB_H, demo.ACCENT, radius=4)


TECHNIQUE = Technique(
    id='scroll-driven-text-reveal',
    name='Scroll-driven text reveal',
    family='typography',
    group='Web and scroll',
    aliases=('scroll-linked type', 'scroll scrub text', 'scroll-linked word highlight', 'reading highlight',
             'word by word fill'),
    definition='Faded text brightens word by word in step with how far the page has been scrolled, '
               'running backwards when the reader scrolls back up.',
    phrasings=('the paragraph lights up as you scroll down the page',
               'words go from grey to white as the scrollbar moves',
               'tie the text fill to the scroll position so it scrubs back and forth'),
    related=('fade-up-scroll-reveal', 'scroll-scrubbed-frame-sequence', 'typewriter-reveal',
             'scroll-linked-background-shift', 'scrollspy-nav-indicator', 'roll-up'),
    api=('videobuilder.techniques.typography.scroll_driven_text_reveal.draw_scroll_text',
         'videobuilder.techniques.typography.scroll_driven_text_reveal.scroll_fill'),
    demo=lambda: demo.film(draw),
)
