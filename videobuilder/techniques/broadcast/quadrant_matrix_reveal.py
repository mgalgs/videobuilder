"""Quadrant matrix reveal: two axes draw on, faint dividers split the plane
into a 2x2 grid, then one card pops into each quadrant in turn."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

QUADRANTS = ('top-left', 'top-right', 'bottom-left', 'bottom-right')


def _arrow(cv, x0, y0, x1, y1, p, color, width):
    """A line from (x0, y0) drawn on to fraction `p`, with an arrowhead once it lands."""
    if p <= 0:
        return
    x, y = x0 + (x1 - x0) * p, y0 + (y1 - y0) * p
    cv.line(x0, y0, x, y, color, width=width)
    if p >= 0.98:
        dx, dy = (1 if x1 > x0 else -1 if x1 < x0 else 0), (1 if y1 > y0 else -1 if y1 < y0 else 0)
        s = width * 4
        # the two barbs, swept back from the tip
        cv.line(x1, y1, x1 - dx * s - dy * s, y1 - dy * s - dx * s, color, width=width)
        cv.line(x1, y1, x1 - dx * s + dy * s, y1 - dy * s + dx * s, color, width=width)


def quadrant_card(cv, cx, cy, title, color, p, w=150, h=56, sub=None):
    """One quadrant item centred at (cx, cy), popping in over `p` (0 -> 1):
    a dark rounded panel outlined in `color`, a dot and a `title`, with an
    optional `sub` line beneath. Type is sized from `h`."""
    if p <= 0:
        return
    s = 0.6 + 0.4 * vb.ease_out_back(p)
    with cv.layer(opacity=vb.clamp01(p * 2.5)):
        w2, h2 = w * s, h * s
        x, y = cx - w2 / 2, cy - h2 / 2
        r = h2 * 0.15
        cv.shadow(x, y, w2, h2, radius=r, dy=r / 2, blur=r * 1.5, color=(0, 0, 0, 0.4))
        cv.rect(x, y, w2, h2, '#1d1f26', radius=r)
        cv.outline(x, y, w2, h2, color, width=max(1.0, h2 * 0.03), radius=r)
        demo.dot(cv, x + h2 * 0.3, cy, r=h2 * 0.08, color=color)
        f = demo.font(max(6, round(h2 * 0.36)), 800)
        ty = cy - h2 * 0.36 if sub else cy - vb.text.line_height(f) / 2
        vb.text.draw(cv, [title], f, x + h2 * 0.54, ty, demo.INK)
        if sub:
            vb.text.draw(cv, [sub], demo.font(max(6, round(h2 * 0.2)), 500), x + h2 * 0.54, cy + h2 * 0.08,
                         demo.MUTED)
    cv.mark(f'card:{title}', cx - w / 2, cy - h / 2, w, h)


def draw_quadrant_matrix(cv, box, p, items, x_label='', y_label='', ends=None, axis=0.3, grid=0.12,
                         color=demo.INK, divider=demo.MUTED):
    """Draw a 2x2 matrix building in at progress `p` (0 -> 1) inside `box`.

    The first `axis` of `p` draws the vertical then horizontal axis on from
    the origin (bottom-left); the next `grid` fades in the dividers that cut
    the plane into quadrants; the rest pops in `items` one after another.
    Each item is `(quadrant, title, color)` or `(quadrant, title, color, sub)`,
    `quadrant` one of `QUADRANTS` (or its index 0-3). `ends` is an optional
    `((x_low, x_high), (y_low, y_high))` pair of axis end labels. Cards,
    type and strokes are sized from `box`.

    In a film: `draw_quadrant_matrix(cv, vb.Box(160, 80, 640, 380), f / frames, items, 'EFFORT', 'IMPACT')`.
    """
    x0, y0, w, h = box.x, box.y, box.w, box.h
    ox, oy = x0, y0 + h                    # origin
    mx, my = x0 + w / 2, y0 + h / 2        # where the dividers cross
    a = vb.clamp01(p / axis)
    k = h / 380                            # type and stroke scale
    stroke = 2 * k
    _arrow(cv, ox, oy, ox, y0, vb.ease_in_out_quart(vb.clamp01(a * 1.6)), color, stroke)
    _arrow(cv, ox, oy, x0 + w, oy, vb.ease_in_out_quart(vb.clamp01(a * 1.6 - 0.6)), color, stroke)

    g = vb.clamp01((p - axis * 0.8) / grid)
    if g > 0:
        gl = vb.ease_out_expo(g)
        cv.line(mx, oy - h * gl, mx, oy, divider, width=2, alpha=0.45)
        cv.line(ox, my, ox + w * gl, my, divider, width=2, alpha=0.45)

    lab = vb.clamp01((p - axis * 0.6) / 0.1)
    if lab > 0:
        lf = demo.font(max(6, round(16 * k)), 800)
        if x_label:
            lw, _ = vb.text.block_size([x_label], lf)
            vb.text.draw(cv, [x_label], lf, mx - lw / 2, oy + 22 * k, color, alpha=lab)
        if y_label:
            vb.text.draw(cv, [y_label], lf, ox + 14 * k, y0 - 8 * k, color, alpha=lab)
        if ends:
            ef = demo.font(max(6, round(11 * k)), 500)
            (xl, xh), (yl, yh) = ends
            vb.text.draw(cv, [xl], ef, ox - 5 * k, oy + 6 * k, demo.MUTED, alpha=lab)
            vb.text.draw(cv, [xh], ef, x0 + w - vb.text.measure(xh, ef), oy + 6 * k, demo.MUTED, alpha=lab)
            vb.text.draw(cv, [yh], ef, ox - 10 * k - vb.text.measure(yh, ef), y0, demo.MUTED, alpha=lab)
            vb.text.draw(cv, [yl], ef, ox - 10 * k - vb.text.measure(yl, ef), oy - 15 * k, demo.MUTED,
                         alpha=lab)

    start = axis + grid
    if items:
        slot = (1 - start) / len(items)
        for i, item in enumerate(items):
            q, title, c = item[:3]
            sub = item[3] if len(item) > 3 else None
            qi = QUADRANTS.index(q) if isinstance(q, str) else q
            cx = x0 + w * (0.25 if qi % 2 == 0 else 0.75)
            cy = y0 + h * (0.25 if qi < 2 else 0.75)
            quadrant_card(cv, cx, cy, title, c, vb.clamp01((p - start - i * slot) / (slot * 0.9)),
                          w=w * 0.34, h=h * 0.2, sub=sub)
    cv.mark('matrix', x0, y0, w, h)


ITEMS = (
    ('top-right', 'Launch', demo.ACCENT, 'big win, big lift'),
    ('top-left', 'Quick fix', demo.TEAL, 'big win, small lift'),
    ('bottom-left', 'Polish', demo.TEAL, 'small win, small lift'),
    ('bottom-right', 'Rebuild', demo.MUTED, 'small win, big lift'),
)


def draw(n, cv):
    draw_quadrant_matrix(cv, vb.Box(165, 70, 670, 390), demo.phase(n, 0.15, 2.7), ITEMS,
                         x_label='EFFORT', y_label='IMPACT', ends=(('Low', 'High'), ('Low', 'High')))


TECHNIQUE = Technique(
    id='quadrant-matrix-reveal',
    name='Quadrant matrix reveal',
    family='broadcast',
    group='Process diagrams',
    aliases=('2x2 matrix build', 'axes quadrant', 'four-box matrix'),
    definition='Two labelled axes draw on and split the frame into four quadrants, '
               'then labelled cards drop into the quadrants one at a time.',
    phrasings=('build up a two-by-two chart and fill each box in turn',
               'animate an impact versus effort grid with items popping into place',
               'draw the axes, then reveal what goes in each of the four corners'),
    related=('hexagon-tile-reveal', 'tile-flip', 'swiss-grid-slide', 'dot-matrix-text', 'heatmap-fill',
             'falling-glyph-rain-reveal'),
    api=('videobuilder.techniques.broadcast.quadrant_matrix_reveal.draw_quadrant_matrix',
         'videobuilder.techniques.broadcast.quadrant_matrix_reveal.quadrant_card'),
    demo=lambda: demo.film(draw),
)
