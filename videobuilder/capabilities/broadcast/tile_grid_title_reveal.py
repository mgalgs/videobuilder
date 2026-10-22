"""Tile grid title reveal: the frame is cut into a grid of tiles that turn,
grow or fade in one after another in a staggered order, each carrying its own
patch of the title card, until the whole card stands assembled."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

STYLES = ('flip', 'scale', 'fade')
ORDERS = ('random', 'diagonal', 'centre', 'columns')


def tile_delays(cols, rows, order='random', seed=0):
    """Start delay of every tile as `{(col, row): 0..1}`, 0 first and 1 last.
    `order` is 'random' (a shuffle fixed by `seed`), 'diagonal' (from the top
    left), 'centre' (outward from the middle) or 'columns' (left to right, each
    column top to bottom)."""
    cells = [(k, r) for r in range(rows) for k in range(cols)]
    if order == 'random':
        ranked = cells[:]
        random.Random(seed).shuffle(ranked)
        key = {c: i for i, c in enumerate(ranked)}
    elif order == 'diagonal':
        key = {(k, r): k + r for k, r in cells}
    elif order == 'centre':
        cx, cy = (cols - 1) / 2, (rows - 1) / 2
        key = {(k, r): math.hypot(k - cx, r - cy) for k, r in cells}
    elif order == 'columns':
        key = {(k, r): k * rows + r for k, r in cells}
    else:
        raise ValueError(f'unknown order {order!r}; orders are {", ".join(ORDERS)}')
    top = max(key.values()) or 1
    return {c: key[c] / top for c in cells}


def tile_grid_reveal(cv, card, p, box=None, cols=6, rows=4, style='flip', order='random', seed=0,
                     stagger=0.7, ease=vb.ease_out_quint, shade=0.6, seams=None, seam_width=1):
    """Draw the title card `card(cv)` (drawn in frame coordinates) revealing at
    progress `p` (0 -> 1) as `cols` x `rows` tiles over `box` (default the
    frame; anything already on the canvas shows through the missing tiles).
    Each tile starts at its `tile_delays` delay times `stagger` and takes the
    rest of `p`, eased by `ease`. `style` 'flip' turns a tile down about its
    horizontal axis, lit up from `shade` darkness as it faces the viewer;
    'scale' grows it from its centre; 'fade' fades it up. With `seams`, a
    hairline of that colour outlines each tile, fading out as `p` ends, so the
    grid reads before the card is whole. At `p >= 1` the card is drawn plainly.

    In a film, call it on each frame of the title's opening, with `card` the
    function that draws the finished title."""
    if style not in STYLES:
        raise ValueError(f'unknown style {style!r}; styles are {", ".join(STYLES)}')
    x0, y0, bw, bh = box if box is not None else (0, 0, cv.width, cv.height)
    if p >= 1:
        with cv.clip(x0, y0, bw, bh):
            card(cv)
        return vb.Box(x0, y0, bw, bh)
    tw, th = bw / cols, bh / rows
    delays = tile_delays(cols, rows, order, seed)
    c = cv.ctx
    for (k, r), d in delays.items():
        t = ease(vb.clamp01((p - stagger * d) / (1 - stagger))) if stagger < 1 else float(p >= 1)
        if t <= 0:
            continue
        x, y = x0 + k * tw, y0 + r * th
        cx, cy = x + tw / 2, y + th / 2
        alpha, sx, sy, dark = 1.0, 1.0, 1.0, 0.0
        if style == 'flip':
            sy, dark = math.sin(t * math.pi / 2), shade * (1 - t)
        elif style == 'scale':
            sx = sy = t
        else:
            alpha = t
        if sx * tw < 0.5 or sy * th < 0.5:
            continue
        c.save()
        c.translate(cx, cy)
        c.scale(sx, sy)
        c.translate(-cx, -cy)
        # Overlap neighbours by half a pixel so finished tiles meet without hairline gaps.
        with cv.clip(x - 0.5, y - 0.5, tw + 1, th + 1), cv.layer(opacity=alpha):
            card(cv)
            if dark > 0.005:
                cv.fill('#000000', alpha=dark)
        c.restore()
    if seams is not None:
        fade = 1 - vb.clamp01((p - 0.8) / 0.2)
        for k in range(cols + 1):
            cv.line(x0 + k * tw, y0, x0 + k * tw, y0 + bh, seams, width=seam_width, alpha=fade)
        for r in range(rows + 1):
            cv.line(x0, y0 + r * th, x0 + bw, y0 + r * th, seams, width=seam_width, alpha=fade)
    return vb.Box(x0, y0, bw, bh)


NAVY = '#26324f'


def title_card(cv):
    """The demo's finished title: a navy plate, an accent band along the top,
    a short rule and the title."""
    cv.fill(NAVY)
    cv.rect(0, 0, demo.W, 18, demo.ACCENT)
    cv.rect(demo.W / 2 - 330, demo.H / 2 - 120, 90, 10, demo.ACCENT)
    demo.word(cv, 'HEADLINE', demo.W / 2, demo.H / 2, size=150, weight=900)
    cv.rect(demo.W / 2 + 240, demo.H / 2 + 110, 90, 10, demo.ACCENT)


def draw(n, cv):
    box = tile_grid_reveal(cv, title_card, demo.phase(n, 0.25, 2.35), cols=8, rows=5, style='flip',
                           order='random', seed=3, stagger=0.75, seams=demo.LINE)
    cv.mark('title', *box)


CAPABILITY = Capability(
    id='tile-grid-title-reveal',
    name='Tile grid title reveal',
    family='broadcast',
    group='Title sequences',
    aliases=('grid mosaic reveal', 'tile wipe title', 'mosaic title reveal', 'tiled title build'),
    definition='A title card arrives piece by piece as a grid of tiles, each flipping, growing or fading '
               'into place at its own moment until the whole card is assembled.',
    phrasings=('build the title screen out of squares that flip in one by one',
               'the opening title appears as a grid of blocks popping in at random',
               'a mosaic of tiles fills the screen and together they form the show title'),
    related=('title-card-reveal', 'tile-flip', 'swiss-grid-slide', 'bento-grid-reveal', 'hexagon-tile-reveal',
             'pixelation-reveal'),
    api=('videobuilder.capabilities.broadcast.tile_grid_title_reveal.tile_grid_reveal',
         'videobuilder.capabilities.broadcast.tile_grid_title_reveal.tile_delays'),
    demo=lambda: demo.film(draw),
)
