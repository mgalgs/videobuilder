"""Context menu origin reveal: a right-click menu grows out of the exact
point that was clicked, its corner pinned to the pointer, scaling up and
fading in, then its rows settling in one after another. Near an edge it
flips so it opens toward the free space, and the corner it grows from flips
with it."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

PANEL, HOVER, RULE = '#23252d', '#ef5b4c', '#33363f'


def menu_placement(x, y, w, h, bounds, gap=4):
    """Where a `w` x `h` menu clicked open at (x, y) goes inside `bounds`
    (a Box): `(left, top, ox, oy)`, the menu's top-left and the origin it
    should grow from. It opens down and to the right of the pointer, and
    flips up and/or left when that would run past `bounds`."""
    b = vb.Box(*bounds)
    right = x + gap + w <= b.x + b.w
    down = y + gap + h <= b.y + b.h
    left = x + gap if right else x - gap - w
    top = y + gap if down else y - gap - h
    return left, top, (left if right else left + w), (top if down else top + h)


def draw_context_menu(cv, x, y, p, items, font=None, bounds=None, width=240, row=40, start_scale=0.3,
                      hover=None, color=PANEL, ink=demo.INK, accent=HOVER, stagger=0.35,
                      ease=vb.ease_out_expo):
    """Draw a context menu clicked open at the pointer (x, y), at reveal
    progress `p` (0 -> 1; run it backwards to close). The panel scales from
    `start_scale` to 1 about the corner nearest the pointer (see
    `menu_placement`; `bounds` defaults to the canvas), fading in as it
    grows, the vertical scale lagging a touch behind the horizontal; the
    rows fade and slide in over the last part, staggered by `stagger`.
    `items` are labels, `None` for a divider; `hover` is the index of a row
    to highlight; `ease` shapes the growth. Returns the menu's Box at full
    size."""
    font = font or demo.font(19, 600)
    rows = [(row * 0.4 if it is None else row) for it in items]
    pad = 8
    w, h = width, sum(rows) + 2 * pad
    left, top, ox, oy = menu_placement(x, y, w, h, bounds or vb.Box.of(cv))
    p = vb.clamp01(p)
    if p <= 0:
        return vb.Box(left, top, w, h)
    sx = start_scale + (1 - start_scale) * ease(p)
    sy = start_scale + (1 - start_scale) * ease(vb.clamp01(p * 1.15 - 0.15))
    c = cv.ctx
    with cv.layer(opacity=vb.clamp01(p * 2.5)):
        c.save()
        c.translate(ox, oy)
        c.scale(sx, sy)
        c.translate(-ox, -oy)
        cv.shadow(left, top, w, h, radius=12, dy=10, blur=26, color=(0, 0, 0, 0.5))
        cv.rect(left, top, w, h, color, radius=12)
        cv.outline(left, top, w, h, RULE, width=1.5, radius=12)
        ry, k = top + pad, 0
        for i, (it, rh) in enumerate(zip(items, rows)):
            if it is None:
                cv.line(left + 14, ry + rh / 2, left + w - 14, ry + rh / 2, RULE, width=1.5)
            else:
                q = vb.clamp01((p - 0.25 - stagger * k / max(1, len(items))) / 0.4)
                q = vb.ease_out_quint(q)
                if i == hover:
                    cv.rect(left + 6, ry + 2, w - 12, rh - 4, accent, radius=8, alpha=q)
                _, th = vb.text.block_size([it], font)
                vb.text.draw(cv, [it], font, left + 20 + 10 * (1 - q), ry + (rh - th) / 2, ink, alpha=q)
                k += 1
            ry += rh
        c.restore()
    cv.mark('menu', left, top, w, h)
    return vb.Box(left, top, w, h)


def _pointer(cv, x, y, s=1.0, color=demo.INK):
    """A mouse-pointer arrow with its tip at (x, y)."""
    pts = [(0, 0), (0, 26), (6.5, 20), (11, 30), (15, 28), (10.5, 18.5), (19, 18.5)]
    c = cv.ctx
    c.new_path()
    for i, (px, py) in enumerate(pts):
        (c.line_to if i else c.move_to)(x + px * s, y + py * s)
    c.close_path()
    c.set_source_rgba(*vb.rgba(color))
    c.fill_preserve()
    c.set_source_rgba(*vb.rgba(demo.BG))
    c.set_line_width(2)
    c.stroke()


ITEMS = ('Copy', 'Paste', 'Duplicate', None, 'Rename', 'Delete')
CLICKS = ((300, 150, 0.55, 1.55, 1), (690, 430, 1.85, 3.2, 4))  # x, y, opens at, closes at, hovered row


def draw(n, cv):
    t = n / demo.FPS
    cv.rect(40, 40, demo.W - 80, demo.H - 80, '#1a1c22', radius=20)
    for gx in range(120, demo.W - 60, 120):
        for gy in range(110, demo.H - 60, 110):
            demo.dot(cv, gx, gy, 2.5, color=demo.LINE)
    # the pointer glides from one click to the next
    (x0, y0, *_), (x1, y1, *_) = CLICKS
    m = vb.ease_in_out_quart(demo.phase(n, 1.55, 1.85))
    px, py = x0 + (x1 - x0) * m, y0 + (y1 - y0) * m
    if t < 0.55:
        k = vb.ease_out_quint(demo.phase(n, 0.0, 0.5))
        px, py = 160 + (x0 - 160) * k, 380 + (y0 - 380) * k
    for x, y, on, off, hov in CLICKS:
        if on - 0.05 <= t < on + 0.35:  # a click ring at the pointer
            r = vb.clamp01((t - on + 0.05) / 0.4)
            cv.arc(x, y, 8 + 26 * r, 0, 6.2832, demo.ACCENT, width=3, alpha=1 - r)
        open_ = demo.phase(n, on, on + 0.6)
        shut = 1 - demo.phase(n, off - 0.12, off) if off < demo.SECONDS else 1
        draw_context_menu(cv, x, y, min(open_, shut), ITEMS, hover=hov if t > on + 0.6 else None,
                          bounds=vb.Box(40, 40, demo.W - 80, demo.H - 80), ease=vb.ease_out_quint)
    _pointer(cv, px, py)
    cv.mark('pointer', px, py, 19, 30)


TECHNIQUE = Technique(
    id='context-menu-origin-reveal',
    name='Context menu origin reveal',
    family='ui',
    group='Overlays & menus',
    aliases=('popover from cursor', 'transform-origin menu', 'right-click menu animation', 'dropdown origin scale'),
    definition='A pop-up menu grows out of the spot where it was clicked, scaling up from the corner at the '
               'pointer as it fades in, and opens away from the screen edge.',
    phrasings=('make the right-click menu pop out from where the mouse is',
               'the dropdown should grow out of the cursor instead of just appearing',
               'animate the menu scaling open from the click point'),
    related=('hamburger-to-x', 'plus-to-close-rotate', 'device-mockup-slide-in', 'hover-lift', 'zoom-out-reveal',
             'corner-wipe'),
    api=('videobuilder.techniques.ui.context_menu_origin_reveal.draw_context_menu',
         'videobuilder.techniques.ui.context_menu_origin_reveal.menu_placement'),
    demo=lambda: demo.film(draw),
)
