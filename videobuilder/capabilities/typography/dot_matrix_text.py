"""Dot-matrix text: letters spelled out on a board of round dots, every dot
either lit or dark, the letters switching on dot by dot as if a display
were drawing them."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

ROWS, COLS = 7, 5  # each glyph is 5 dots wide, 7 tall, with one dark column between glyphs

# A 5x7 font, one byte per column left to right, bit 0 the top row.
FONT = {
    ' ': (0x00, 0x00, 0x00, 0x00, 0x00), '!': (0x00, 0x00, 0x5F, 0x00, 0x00),
    "'": (0x00, 0x05, 0x03, 0x00, 0x00), '+': (0x08, 0x08, 0x3E, 0x08, 0x08),
    ',': (0x00, 0x50, 0x30, 0x00, 0x00), '-': (0x08, 0x08, 0x08, 0x08, 0x08),
    '.': (0x00, 0x60, 0x60, 0x00, 0x00), '/': (0x20, 0x10, 0x08, 0x04, 0x02),
    ':': (0x00, 0x36, 0x36, 0x00, 0x00), '?': (0x02, 0x01, 0x51, 0x09, 0x06),
    '0': (0x3E, 0x51, 0x49, 0x45, 0x3E), '1': (0x00, 0x42, 0x7F, 0x40, 0x00),
    '2': (0x42, 0x61, 0x51, 0x49, 0x46), '3': (0x21, 0x41, 0x45, 0x4B, 0x31),
    '4': (0x18, 0x14, 0x12, 0x7F, 0x10), '5': (0x27, 0x45, 0x45, 0x45, 0x39),
    '6': (0x3C, 0x4A, 0x49, 0x49, 0x30), '7': (0x01, 0x71, 0x09, 0x05, 0x03),
    '8': (0x36, 0x49, 0x49, 0x49, 0x36), '9': (0x06, 0x49, 0x49, 0x29, 0x1E),
    'A': (0x7E, 0x11, 0x11, 0x11, 0x7E), 'B': (0x7F, 0x49, 0x49, 0x49, 0x36),
    'C': (0x3E, 0x41, 0x41, 0x41, 0x22), 'D': (0x7F, 0x41, 0x41, 0x22, 0x1C),
    'E': (0x7F, 0x49, 0x49, 0x49, 0x41), 'F': (0x7F, 0x09, 0x09, 0x09, 0x01),
    'G': (0x3E, 0x41, 0x49, 0x49, 0x7A), 'H': (0x7F, 0x08, 0x08, 0x08, 0x7F),
    'I': (0x00, 0x41, 0x7F, 0x41, 0x00), 'J': (0x20, 0x40, 0x41, 0x3F, 0x01),
    'K': (0x7F, 0x08, 0x14, 0x22, 0x41), 'L': (0x7F, 0x40, 0x40, 0x40, 0x40),
    'M': (0x7F, 0x02, 0x0C, 0x02, 0x7F), 'N': (0x7F, 0x04, 0x08, 0x10, 0x7F),
    'O': (0x3E, 0x41, 0x41, 0x41, 0x3E), 'P': (0x7F, 0x09, 0x09, 0x09, 0x06),
    'Q': (0x3E, 0x41, 0x51, 0x21, 0x5E), 'R': (0x7F, 0x09, 0x19, 0x29, 0x46),
    'S': (0x46, 0x49, 0x49, 0x49, 0x31), 'T': (0x01, 0x01, 0x7F, 0x01, 0x01),
    'U': (0x3F, 0x40, 0x40, 0x40, 0x3F), 'V': (0x1F, 0x20, 0x40, 0x20, 0x1F),
    'W': (0x3F, 0x40, 0x38, 0x40, 0x3F), 'X': (0x63, 0x14, 0x08, 0x14, 0x63),
    'Y': (0x07, 0x08, 0x70, 0x08, 0x07), 'Z': (0x61, 0x51, 0x49, 0x45, 0x43),
}


def matrix_size(text):
    """`(cols, rows)` of the dot board that spells `text` on one line."""
    return max(0, len(text) * (COLS + 1) - 1), ROWS


def dot_matrix(text, p=1.0, stagger=0.6):
    """`text` as a board of dots: `(col, row, lit)` for every dot. Letters are
    upper-cased; a character the font lacks shows as `?`. At progress `p`
    (0 -> 1) each letter's dots switch on one by one, column by column from
    the top, the letters starting `stagger` of the way apart in turn (0: all
    together, 1: one after another); at `p >= 1` the text is whole."""
    p = vb.clamp01(p)
    cols, _ = matrix_size(text)
    n = max(1, len(text))
    span = 1 - stagger * (n - 1) / n  # how long each letter takes to draw
    out = []
    for i, ch in enumerate(text.upper()):
        glyph = FONT.get(ch, FONT['?'])
        on = [(c, r) for c in range(COLS) for r in range(ROWS) if glyph[c] >> r & 1]
        start = stagger * i / n
        shown = len(on) if p >= 1 else int(vb.clamp01((p - start) / span) * len(on) + 1e-9)
        lit = set(on[:shown])
        for c in range(COLS):
            for r in range(ROWS):
                out.append((i * (COLS + 1) + c, r, (c, r) in lit))
        if i * (COLS + 1) + COLS < cols:
            out.extend((i * (COLS + 1) + COLS, r, False) for r in range(ROWS))
    return out


def draw_dot_matrix(cv, text, x, y, pitch, p=1.0, on=demo.INK, off=demo.LINE, radius=0.36, glow=0.18,
                    pad=1, panel=None, **kw):
    """Draw `text` as dot-matrix type from its top-left (x, y), one dot every
    `pitch` px, `radius` a fraction of the pitch. Lit dots are `on` with a
    soft halo `glow` strong (0 for none); dark dots stay visible as `off`.
    `pad` adds dark dots round the edge, and `panel` fills a rounded board
    behind them. `p` and `kw` go to `dot_matrix`. Returns the board's Box."""
    cols, rows = matrix_size(text)
    w, h = (cols + 2 * pad) * pitch, (rows + 2 * pad) * pitch
    if panel:
        cv.rect(x, y, w, h, panel, radius=pitch * 0.8)
    r = pitch * radius
    for c, row in [(c, row) for c in range(-pad, cols + pad) for row in range(-pad, rows + pad)
                   if not (0 <= c < cols and 0 <= row < rows)]:
        demo.dot(cv, x + (c + pad + 0.5) * pitch, y + (row + pad + 0.5) * pitch, r, off)
    for c, row, lit in dot_matrix(text, p, **kw):
        cx, cy = x + (c + pad + 0.5) * pitch, y + (row + pad + 0.5) * pitch
        if lit and glow:
            demo.dot(cv, cx, cy, r * 1.9, on, alpha=glow)
        demo.dot(cv, cx, cy, r, on if lit else off)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    text, pitch = 'DOT MATRIX', 13
    cols, rows = matrix_size(text)
    w, h = (cols + 2) * pitch, (rows + 2) * pitch
    box = draw_dot_matrix(cv, text, (demo.W - w) / 2, (demo.H - h) / 2, pitch, demo.phase(n, 0.3, 2.2),
                          on=demo.ACCENT, panel='#0d0e12')
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='dot-matrix-text',
    name='Dot-matrix text',
    family='typography',
    group='Mechanical display',
    aliases=('LED matrix type', 'pixel grid text', 'dot matrix display'),
    definition='Letters are built from a fixed grid of round dots, each either switched on or left dark, '
               'and the words appear as the dots light up.',
    phrasings=('make the title look like an LED sign made of little lights',
               'spell the words out in glowing dots like a departure board',
               'text that lights up dot by dot on a grid'),
    related=('scrolling-led-marquee-text', 'pixel-sort-text', 'dot-grid-displacement', 'ascii-art-render',
             'falling-glyph-rain-reveal', 'pixelation-reveal'),
    api=('videobuilder.capabilities.typography.dot_matrix_text.draw_dot_matrix',
         'videobuilder.capabilities.typography.dot_matrix_text.dot_matrix',
         'videobuilder.capabilities.typography.dot_matrix_text.matrix_size'),
    demo=lambda: demo.film(draw),
)
