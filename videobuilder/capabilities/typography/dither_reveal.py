"""Dither Reveal: the same idea as Bayer ordered dithering
(`../vfx/bayer_ordered_dithering.py`), which keeps the capability -- both
threshold against the same tiled Bayer matrix (`bayer`), this one sweeping
the threshold over time so cells fill in until a word is solid. This
module's own code stays (a film may still import it), but it is no longer a
capability of its own."""
import videobuilder as vb

from .. import _demo as demo

MERGED_INTO = 'bayer-ordered-dithering'


def bayer(order=3):
    """The `2**order` square Bayer matrix as rows of thresholds in [0, 1):
    each value is when that cell turns on, spread so every stage is an even
    scatter of dots rather than a clump."""
    m = [[0]]
    for _ in range(order):
        n = len(m)
        m = [[4 * m[y % n][x % n] + (0, 2, 3, 1)[(y // n) * 2 + x // n] for x in range(2 * n)]
             for y in range(2 * n)]
    size = len(m) ** 2
    return [[v / size for v in row] for row in m]


def dither_reveal(cv, box, p, draw, cell=8, order=3, gap=0.35):
    """Draw `draw(cv)` seen through an ordered dither screen over `box` at
    progress `p` (0 -> 1): nothing at 0, solid at 1, and between, the cells of
    a `cell`-px grid whose Bayer threshold is below `p`. The cells start as
    dots `gap` of a cell apart and close up as `p` runs, so the end is seamless.
    Works for anything `draw` paints: a word, a logo, an image."""
    p = vb.clamp01(p)
    if p <= 0:
        return
    if p >= 1:
        draw(cv)
        return
    m = bayer(order)
    k = len(m)
    side = cell * (1 - gap * (1 - p))
    inset = (cell - side) / 2
    x0, y0, w, h = box
    ctx = cv.ctx
    ctx.save()
    ctx.new_path()
    for j in range(int(h // cell) + 1):
        row = m[j % k]
        for i in range(int(w // cell) + 1):
            if row[i % k] < p:
                ctx.rectangle(x0 + i * cell + inset, y0 + j * cell + inset, side, side)
    ctx.clip()
    draw(cv)
    ctx.restore()


def draw_dither_text(cv, text, font, x, y, p, color, **kw):
    """Draw `text` from its top-left (x, y) dithering in at progress `p`.
    `kw` goes to `dither_reveal`. Returns the Box of the finished line."""
    w, h = vb.text.block_size([text], font)
    box = vb.Box(x, y, w, h)
    dither_reveal(cv, box, p, lambda c: vb.text.draw(c, [text], font, x, y, color), **kw)
    return box


def draw(n, cv):
    f = demo.font(200, 900)
    text = 'DITHER'
    w, h = vb.text.block_size([text], f)
    p = demo.phase(n, 0.3, 2.85)
    box = draw_dither_text(cv, text, f, (demo.W - w) / 2, (demo.H - h) / 2, p, demo.INK, cell=10)
    cv.mark('text', *box)
