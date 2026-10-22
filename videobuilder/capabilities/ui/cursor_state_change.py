"""Cursor state change: a custom pointer that, over something clickable,
folds its arrow away and swells into a round badge with a word in it, then
shrinks back to the arrow when it leaves."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

# The arrow pointer, tip at (0, 0), in pixels at size 1.
ARROW = ((0, 0), (0, 27), (7, 21), (12, 32), (17.5, 29.5), (12.5, 19), (21, 19))


def hover_amount(x, y, box, reach=36):
    """How far a pointer at (x, y) is into its hover state over `box` (a
    `vb.Box` or `(x, y, w, h)`), 0 -> 1: 1 inside the box, falling to 0
    `reach` pixels outside it, eased, so a moving pointer morphs over a few
    frames instead of snapping."""
    bx, by, bw, bh = box
    dx = max(bx - x, 0, x - (bx + bw))
    dy = max(by - y, 0, y - (by + bh))
    return vb.ease_in_out_quart(1 - vb.clamp01(math.hypot(dx, dy) / reach))


def draw_cursor(cv, x, y, hover, label=None, color=demo.INK, ink=demo.BG, radius=46, size=1.0,
                font=None):
    """A pointer with its tip at (x, y) in state `hover` (0 = arrow, 1 = over
    a target). As `hover` rises the arrow shrinks into its tip while a disc
    of `radius` grows there in `color`, and `label` fades in on the disc in
    `ink`; at 0 it is a plain arrow with a dark outline. `size` scales it
    all. Returns the Box it covers."""
    h = vb.clamp01(hover)
    fold = vb.clamp01(h / 0.5)                      # arrow is gone by half-way
    grow = vb.ease_out_back(vb.clamp01((h - 0.15) / 0.85))
    r = radius * size * grow
    if r > 0.5:
        cv.sector(x, y, r, 0, 2 * math.pi, color, alpha=0.92)
        if label and h > 0.6:
            f = font or demo.font(round(15 * size), 800)
            w, th = vb.text.block_size([label], f)
            vb.text.draw(cv, [label], f, x - w / 2, y - th / 2, ink, alpha=vb.clamp01((h - 0.6) / 0.4))
    s = size * (1 - fold)
    if s > 0.02:
        pts = [(x + px * s, y + py * s) for px, py in ARROW]
        c = cv.ctx
        cv.shape_shadow(pts, dx=2 * s, dy=4 * s, blur=6, color=(0, 0, 0, 0.45))
        c.new_path()
        c.move_to(*pts[0])
        for p in pts[1:]:
            c.line_to(*p)
        c.close_path()
        c.set_source_rgba(*vb.rgba(color))
        c.fill_preserve()
        c.set_source_rgba(*vb.rgba(ink))
        c.set_line_width(2 * s)
        c.stroke()
    reach = max(radius * size, 32 * size)
    return vb.Box(x - reach, y - reach, 2 * reach, 2 * reach)


def draw(n, cv):
    W, H = demo.W, demo.H
    cw, ch = 440, 260
    cx0, cy0 = (W - cw) / 2, (H - ch) / 2
    cv.shadow(cx0, cy0, cw, ch, radius=18, dy=10, blur=28, color=(0, 0, 0, 0.45))
    cv.rect(cx0, cy0, cw, ch, demo.LINE, radius=18)
    cv.rect(cx0 + 36, cy0 + 40, 190, 12, demo.MUTED, radius=6, alpha=0.9)
    cv.rect(cx0 + 36, cy0 + 68, 300, 10, demo.MUTED, radius=5, alpha=0.5)
    cv.rect(cx0 + 36, cy0 + 90, 250, 10, demo.MUTED, radius=5, alpha=0.5)
    button = vb.Box(cx0 + 36, cy0 + ch - 88, 150, 52)

    # The pointer drifts in from the right, rests on the button, then wanders off.
    rest = (button.x + button.w * 0.6, button.y + button.h * 0.55)
    start, away = (W - 150, H / 2 + 150), (cx0 + cw - 40, cy0 + ch - 120)
    go = vb.ease_in_out_quart(demo.phase(n, 0.3, 1.2))
    back = vb.ease_in_out_quart(demo.phase(n, 2.0, 2.7))
    x = start[0] + (rest[0] - start[0]) * go + (away[0] - rest[0]) * back
    y = start[1] + (rest[1] - start[1]) * go + (away[1] - rest[1]) * back
    hover = hover_amount(x, y, button)

    cv.rect(*button, demo.ACCENT, radius=12, alpha=0.75 + 0.25 * hover)
    cv.mark('button', *button)
    cv.mark('cursor', *draw_cursor(cv, x, y, hover, label='OPEN'))


TECHNIQUE = Technique(
    id='cursor-state-change',
    name='Cursor state change',
    family='ui',
    group='Cursor & hover',
    aliases=('contextual cursor', 'cursor morph on target', 'hover cursor'),
    definition='A custom pointer that changes form when it reaches something clickable, '
               'here swelling from an arrow into a labelled disc and shrinking back as it leaves.',
    phrasings=('the mouse pointer turns into a big circle that says "open" over the button',
               'the cursor morphs when it hovers a link and goes back to an arrow after',
               'a custom cursor that reacts to what it is pointing at'),
    related=('cursor-path-animation', 'magnetic-button', 'blinking-cursor', 'cursor-follow-auto-zoom',
             'dot-grid-displacement', 'proximity-stagger'),
    api=('videobuilder.techniques.ui.cursor_state_change.draw_cursor',
         'videobuilder.techniques.ui.cursor_state_change.hover_amount'),
    demo=lambda: demo.film(draw),
)
