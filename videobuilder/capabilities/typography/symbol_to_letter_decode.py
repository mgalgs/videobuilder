"""Symbol-to-letter decode: a row of line icons stands where a word will be,
and one by one, left to right, each icon shrinks away and a letter pops in
its place until the word is spelt out."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _circle_plus(c, r):
    c.new_sub_path()
    c.arc(0, 0, r, 0, 2 * math.pi)
    c.move_to(-r * 0.5, 0)
    c.line_to(r * 0.5, 0)
    c.move_to(0, -r * 0.5)
    c.line_to(0, r * 0.5)


def _triangle(c, r):
    c.move_to(-r, -r * 0.8)
    c.line_to(r, -r * 0.8)
    c.line_to(0, r * 0.9)
    c.close_path()


def _burst(c, r):
    for i in range(8):
        a = i * math.pi / 4
        c.move_to(r * 0.4 * math.cos(a), r * 0.4 * math.sin(a))
        c.line_to(r * math.cos(a), r * math.sin(a))


def _square_minus(c, r):
    k = r * 0.3
    c.move_to(-r + k, -r)
    c.arc(r - k, -r + k, k, -math.pi / 2, 0)
    c.arc(r - k, r - k, k, 0, math.pi / 2)
    c.arc(-r + k, r - k, k, math.pi / 2, math.pi)
    c.arc(-r + k, -r + k, k, math.pi, 3 * math.pi / 2)
    c.close_path()
    c.move_to(-r * 0.5, 0)
    c.line_to(r * 0.5, 0)


def _zigzag(c, r):
    c.move_to(-r, r * 0.6)
    c.line_to(-r * 0.35, -r * 0.6)
    c.line_to(r * 0.1, r * 0.6)
    c.line_to(r, -r * 0.6)


def _diamond(c, r):
    c.move_to(0, -r)
    c.line_to(r, 0)
    c.line_to(0, r)
    c.line_to(-r, 0)
    c.close_path()


def _ring(c, r):
    c.new_sub_path()
    c.arc(0, 0, r, 0, 2 * math.pi)
    c.new_sub_path()
    c.arc(0, 0, r * 0.35, 0, 2 * math.pi)


def _cross(c, r):
    k = r * 0.75
    c.move_to(-k, -k)
    c.line_to(k, k)
    c.move_to(k, -k)
    c.line_to(-k, k)


ICONS = {'circle-plus': _circle_plus, 'triangle': _triangle, 'burst': _burst, 'square-minus': _square_minus,
         'zigzag': _zigzag, 'diamond': _diamond, 'ring': _ring, 'cross': _cross}
CYCLE = ('ring', 'circle-plus', 'triangle', 'burst', 'square-minus', 'zigzag', 'diamond', 'cross')


def draw_icon(cv, name, cx, cy, size, color, width=None, alpha=1.0):
    """The line icon `name` (a key of `ICONS`) centred at (cx, cy), `size`
    across, stroked in `color` with round ends; `width` defaults to a twelfth
    of `size`."""
    c = cv.ctx
    c.save()
    c.translate(cx, cy)
    c.new_path()
    ICONS[name](c, size / 2)
    c.set_source_rgba(*vb.canvas.rgba(color, alpha))
    c.set_line_width(width or size / 12)
    c.set_line_cap(1)   # cairo LINE_CAP_ROUND
    c.set_line_join(1)  # cairo LINE_JOIN_ROUND
    c.stroke()
    c.restore()


def swap_progress(i, count, p, overlap=0.5):
    """How far character `i` of `count` is through its swap (0 -> 1) at
    overall progress `p`. Swaps run left to right, each overlapping the next
    by `overlap` of its own length."""
    span = 1 / (count - (count - 1) * overlap) if count > 1 else 1
    return vb.clamp01((p - i * span * (1 - overlap)) / span)


def draw_symbol_decode(cv, text, font, x, y, p, color, symbol_color=None, symbols=CYCLE, tracking=0.0,
                       icon_size=None, overlap=0.5):
    """Draw `text` from its top-left (x, y) at progress `p` (0 -> 1): each
    letter starts as a line icon from `symbols` (cycled, in `symbol_color`,
    default `color`) and swaps to the letter in turn, left to right -- the
    icon shrinks and fades, the letter pops up through it. `tracking` adds
    space after each letter; `icon_size` defaults to the cap height. Spaces
    stay blank. Returns the Box of the finished line."""
    w, h = vb.text.block_size([text], font)
    w += tracking * (len(text) - 1)
    size = icon_size or font.size * 0.62
    cy = y + h / 2
    left = x
    for i, ch in enumerate(text):
        adv = vb.text.measure(ch, font)
        cx = left + adv / 2
        left += adv + tracking
        if ch.isspace():
            continue
        k = swap_progress(i, len(text), p, overlap)
        out = vb.clamp01(k / 0.45)
        if out < 1:
            s = 1 - 0.7 * vb.ease_in_expo(out)
            draw_icon(cv, symbols[i % len(symbols)], cx, cy, size * s, symbol_color or color,
                      width=size / 12, alpha=1 - out)
        into = vb.clamp01((k - 0.3) / 0.7)
        if into > 0:
            s = 0.4 + 0.6 * vb.ease_out_back(into)
            lw, lh = vb.text.block_size([ch], font)
            with cv.layer(opacity=min(1.0, into * 2.5), dx=cx, dy=cy, scale=s):
                vb.text.draw(cv, [ch], font, -lw / 2, -lh / 2, color)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    f = demo.font(96, 800)
    text, tracking = 'MOTION', 30
    w, h = vb.text.block_size([text], f)
    w += tracking * (len(text) - 1)
    box = draw_symbol_decode(cv, text, f, (demo.W - w) / 2, (demo.H - h) / 2, demo.phase(n, 0.5, 2.4),
                             demo.INK, symbol_color=demo.ACCENT, tracking=tracking)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='symbol-to-letter-decode',
    name='Symbol-to-letter decode',
    family='typography',
    group='Glyph swaps',
    aliases=('icon to text swap', 'pictogram to type'),
    definition='A line of small icons holds the place of a word, and each icon in turn gives way to a letter '
               'until the whole word is spelled out.',
    phrasings=('start with a row of icons that turn into the letters of the title one at a time',
               'swap each symbol for a letter so the word reveals itself',
               'little pictograms that decode into the brand name'),
    related=('text-to-shape-morph', 'scramble-decode', 'pictogram-counting', 'ascii-art-render',
             'icon-state-morph', 'character-slide-in'),
    api=('videobuilder.capabilities.typography.symbol_to_letter_decode.draw_symbol_decode',
         'videobuilder.capabilities.typography.symbol_to_letter_decode.draw_icon',
         'videobuilder.capabilities.typography.symbol_to_letter_decode.swap_progress'),
    demo=lambda: demo.film(draw),
)
