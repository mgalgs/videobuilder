"""Scrolling LED marquee text: a line of dot-matrix lettering slides across
a panel of lamps, entering at the right edge and leaving at the left, a
whole column of lamps at a time."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

# A 5x7 lamp font: each glyph is seven rows of five lamps, top to bottom.
FONT = {
    'A': '01110 10001 10001 11111 10001 10001 10001',
    'B': '11110 10001 10001 11110 10001 10001 11110',
    'C': '01110 10001 10000 10000 10000 10001 01110',
    'D': '11110 10001 10001 10001 10001 10001 11110',
    'E': '11111 10000 10000 11110 10000 10000 11111',
    'F': '11111 10000 10000 11110 10000 10000 10000',
    'G': '01110 10001 10000 10111 10001 10001 01111',
    'H': '10001 10001 10001 11111 10001 10001 10001',
    'I': '01110 00100 00100 00100 00100 00100 01110',
    'J': '00111 00010 00010 00010 00010 10010 01100',
    'K': '10001 10010 10100 11000 10100 10010 10001',
    'L': '10000 10000 10000 10000 10000 10000 11111',
    'M': '10001 11011 10101 10101 10001 10001 10001',
    'N': '10001 10001 11001 10101 10011 10001 10001',
    'O': '01110 10001 10001 10001 10001 10001 01110',
    'P': '11110 10001 10001 11110 10000 10000 10000',
    'Q': '01110 10001 10001 10001 10101 10010 01101',
    'R': '11110 10001 10001 11110 10100 10010 10001',
    'S': '01111 10000 10000 01110 00001 00001 11110',
    'T': '11111 00100 00100 00100 00100 00100 00100',
    'U': '10001 10001 10001 10001 10001 10001 01110',
    'V': '10001 10001 10001 10001 10001 01010 00100',
    'W': '10001 10001 10001 10101 10101 10101 01010',
    'X': '10001 10001 01010 00100 01010 10001 10001',
    'Y': '10001 10001 01010 00100 00100 00100 00100',
    'Z': '11111 00001 00010 00100 01000 10000 11111',
    '0': '01110 10001 10011 10101 11001 10001 01110',
    '1': '00100 01100 00100 00100 00100 00100 01110',
    '2': '01110 10001 00001 00010 00100 01000 11111',
    '3': '11111 00010 00100 00010 00001 10001 01110',
    '4': '00010 00110 01010 10010 11111 00010 00010',
    '5': '11111 10000 11110 00001 00001 10001 01110',
    '6': '00110 01000 10000 11110 10001 10001 01110',
    '7': '11111 00001 00010 00100 01000 01000 01000',
    '8': '01110 10001 10001 01110 10001 10001 01110',
    '9': '01110 10001 10001 01111 00001 00010 01100',
    ' ': '00000 00000 00000 00000 00000 00000 00000',
    '.': '00000 00000 00000 00000 00000 01100 01100',
    ',': '00000 00000 00000 00000 01100 00100 01000',
    '!': '00100 00100 00100 00100 00100 00000 00100',
    '?': '01110 10001 00001 00010 00100 00000 00100',
    '-': '00000 00000 00000 11111 00000 00000 00000',
    ':': '00000 01100 01100 00000 01100 01100 00000',
    "'": '00100 00100 01000 00000 00000 00000 00000',
    '/': '00000 00001 00010 00100 01000 10000 00000',
    '+': '00000 00100 00100 11111 00100 00100 00000',
    '*': '00000 00100 10101 01110 10101 00100 00000',
    '#': '01010 01010 11111 01010 11111 01010 01010',
    '$': '00100 01111 10100 01110 00101 11110 00100',
    '%': '11000 11001 00010 00100 01000 10011 00011',
    '&': '01100 10010 10100 01000 10101 10010 01101',
}
GLYPH_ROWS = 7


def led_columns(text, gap=1):
    """`text` as lamp columns, left to right: each column is a tuple of
    `GLYPH_ROWS` booleans, top to bottom. Letters are 5 columns wide with
    `gap` dark columns after each. Lower case is shown as upper case; a
    character the font lacks shows as a blank."""
    blank = FONT[' ']
    cols = []
    for ch in text.upper():
        rows = FONT.get(ch, blank).split()
        cols += [tuple(r[c] == '1' for r in rows) for c in range(5)]
        cols += [(False,) * GLYPH_ROWS] * gap
    return cols


def marquee_shift(p, text_cols, panel_cols):
    """The panel column the text's first column sits at, progress `p` 0 -> 1:
    `panel_cols` (just off the right edge) at 0, `-text_cols` (just gone off
    the left) at 1. Whole columns only, as a real sign steps."""
    return math.floor(panel_cols - vb.clamp01(p) * (panel_cols + text_cols))


def draw_led_marquee(cv, text, x, y, cols, p, pitch=20, on=demo.ACCENT, off=None, panel='#0b0c0f',
                     glow=True, pad=1, gap=1):
    """Draw an LED sign `cols` lamps wide from its top-left (x, y), with
    `text` scrolled across it at progress `p` (0: about to enter from the
    right; 1: just left at the left). Lamps are `pitch` apart; `pad` dark
    rows sit above and below the lettering. `on` is the lit colour, `off`
    the unlit lamps' (default `on`, faint); `glow` adds a soft halo to lit
    lamps; `panel` is the housing (None for none). Returns the panel's Box."""
    lit = led_columns(text, gap)
    rows = GLYPH_ROWS + 2 * pad
    w, h = cols * pitch, rows * pitch
    if panel:
        cv.rect(x - pitch * 0.6, y - pitch * 0.6, w + pitch * 1.2, h + pitch * 1.2, panel, radius=pitch * 0.8)
    shift = marquee_shift(p, len(lit), cols)
    r = pitch * 0.36
    for c in range(cols):
        src = c - shift
        column = lit[src] if 0 <= src < len(lit) else ()
        cx = x + (c + 0.5) * pitch
        for row in range(rows):
            cy = y + (row + 0.5) * pitch
            g = row - pad
            if 0 <= g < GLYPH_ROWS and column and column[g]:
                if glow:
                    demo.dot(cv, cx, cy, r * 1.9, on, alpha=0.18)
                demo.dot(cv, cx, cy, r, on)
            else:
                demo.dot(cv, cx, cy, r, off or on, alpha=1.0 if off else 0.1)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    cols, pitch = 56, 14
    w = cols * pitch
    h = (GLYPH_ROWS + 2) * pitch
    box = draw_led_marquee(cv, 'NOW SHOWING', (demo.W - w) / 2, (demo.H - h) / 2, cols,
                           demo.phase(n, 0.0, demo.SECONDS), pitch=pitch)
    cv.mark('sign', *box)


CAPABILITY = Capability(
    id='scrolling-led-marquee-text',
    name='Scrolling LED marquee text',
    family='typography',
    group='Looping and marquee',
    aliases=('LED sign scroll', 'dot-matrix marquee', 'LED ticker'),
    definition='Words built from glowing lamp dots step sideways across a grid of dim lamps, '
               'coming in at one edge and running out at the other.',
    phrasings=('make the title crawl past like a lit-up sign over a shop door',
               'text sliding along a board of little light bulbs',
               'a scrolling message on a dotted LED display'),
    related=('dot-matrix-text', 'scroll-driven-text-reveal', 'infinite-marquee', 'fade-up-scroll-reveal',
             'scroll-linked-background-shift', 'scrollspy-nav-indicator'),
    api=('videobuilder.capabilities.typography.scrolling_led_marquee_text.draw_led_marquee',
         'videobuilder.capabilities.typography.scrolling_led_marquee_text.led_columns',
         'videobuilder.capabilities.typography.scrolling_led_marquee_text.marquee_shift'),
    demo=lambda: demo.film(draw),
)
