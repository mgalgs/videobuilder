"""Bookmark Fill: an outlined bookmark icon is clicked, colour rises inside it
from the bottom until it is solid, and the icon gives a small springy pop as
it lands in its saved state."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def bookmark_path(ctx, cx, cy, w, h, notch=0.24, radius=0.12):
    """Trace a bookmark (a tall ribbon with a V cut into its foot) centred at
    (cx, cy) on the cairo context `ctx`, as a new closed path. `notch` is the
    V's depth and `radius` the top corners' rounding, both as fractions of `w`."""
    x, y, r = cx - w / 2, cy - h / 2, w * radius
    ctx.new_path()
    ctx.move_to(x, y + h)
    ctx.line_to(x, y + r)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.arc(x + w - r, y + r, r, 1.5 * math.pi, 2 * math.pi)
    ctx.line_to(x + w, y + h)
    ctx.line_to(cx, y + h - w * notch * 1.6)
    ctx.close_path()


def draw_bookmark(cv, cx, cy, level, w=90, h=130, color=demo.ACCENT, line=demo.INK, stroke=6, scale=1.0):
    """A bookmark icon centred at (cx, cy), filled with `color` from the bottom
    up to `level` (0 empty outline -> 1 solid). Its outline shifts from `line`
    to `color` as it fills; `scale` grows it about its centre. Returns its Box."""
    level = vb.clamp01(level)
    c = cv.ctx
    c.save()
    c.translate(cx, cy)
    c.scale(scale, scale)
    if level > 0:
        c.save()
        bookmark_path(c, 0, 0, w, h)
        c.clip()
        c.rectangle(-w, h / 2 - h * level, 2 * w, h * level + 1)
        c.set_source_rgba(*vb.canvas.rgba(color))
        c.fill()
        c.restore()
    bookmark_path(c, 0, 0, w, h)
    edge = vb.clamp01(level * 4)  # the outline takes the fill's colour early on
    a, b = vb.canvas.rgba(line), vb.canvas.rgba(color)
    c.set_source_rgba(*(u + (v - u) * edge for u, v in zip(a, b)))
    c.set_line_width(stroke)
    c.set_line_join(1)  # round
    c.stroke()
    c.restore()
    return vb.Box(cx - w * scale / 2, cy - h * scale / 2, w * scale, h * scale)


def saved_pop(t, squash=0.18):
    """The icon's scale `t` seconds after it fills: it starts squashed by
    `squash` and springs back past 1 before settling there. 1 before t = 0."""
    if t <= 0:
        return 1.0
    return 1 - squash + squash * vb.spring(t, stiffness=320, damping=11)


def bookmark_fill(cv, cx, cy, t, fill=0.45, **kw):
    """The whole save: a bookmark at (cx, cy) `t` seconds after it is clicked.
    It fills from the bottom over `fill` seconds (eased out), then pops (see
    `saved_pop`). Before t = 0 it is an empty outline. `kw` goes to
    `draw_bookmark`. Returns its Box."""
    level = 1 - (1 - vb.clamp01(t / fill)) ** 3
    return draw_bookmark(cv, cx, cy, level, scale=saved_pop(t - fill), **kw)


CLICK = 1.0  # seconds into the demo when the cursor clicks


def _cursor(cv, x, y, press):
    """A plain arrow pointer with its tip at (x, y), dipping slightly when pressed."""
    s = 1 - 0.12 * press
    pts = [(0, 0), (0, 34), (9, 26), (15, 40), (21, 37), (15, 24), (26, 24)]
    c = cv.ctx
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    c.new_path()
    for i, (px, py) in enumerate(pts):
        (c.line_to if i else c.move_to)(px, py)
    c.close_path()
    c.set_source_rgba(*vb.canvas.rgba(demo.INK))
    c.fill_preserve()
    c.set_source_rgba(*vb.canvas.rgba(demo.BG))
    c.set_line_width(2.5)
    c.stroke()
    c.restore()


def draw(n, cv):
    with cv.layer(dx=demo.W / 2, dy=demo.H / 2, scale=1.45), cv.layer(dx=-demo.W / 2, dy=-demo.H / 2):
        _scene(n, cv)


def _scene(n, cv):
    t = n / demo.FPS
    cw, ch = 560, 300
    x, y = (demo.W - cw) / 2, (demo.H - ch) / 2
    cv.shadow(x, y, cw, ch, radius=24, dy=12, blur=30, color=(0, 0, 0, 0.45))
    cv.rect(x, y, cw, ch, '#1d1f26', radius=24)
    cv.outline(x, y, cw, ch, demo.LINE, width=2, radius=24)
    for i, frac in enumerate((0.5, 0.38, 0.3)):
        cv.rect(x + 44, y + 60 + 34 * i, cw * frac, 12, demo.MUTED, radius=6, alpha=0.7)
    cv.rect(x + 44, y + ch - 82, 120, 34, demo.TEAL, radius=17)
    bx, by = x + cw - 120, y + ch / 2
    box = bookmark_fill(cv, bx, by, t - CLICK, w=100, h=150, stroke=7)
    cv.mark('bookmark', *box)
    if t >= CLICK:  # a soft ring spreads from the click
        r = demo.phase(n, CLICK, CLICK + 0.5)
        if r < 1:
            cv.arc(bx, by + 10, 18 + 50 * r, 0, 2 * math.pi, demo.INK, width=3, alpha=0.5 * (1 - r))
    move = 1 - (1 - demo.phase(n, 0.2, CLICK - 0.05)) ** 3
    leave = demo.phase(n, CLICK + 0.7, CLICK + 1.3) ** 2
    px = demo.W / 2 + 330 + (bx - demo.W / 2 - 330) * move + 260 * leave
    py = demo.H / 2 + 230 + (by + 10 - demo.H / 2 - 230) * move + 160 * leave
    press = max(0.0, 1 - abs(t - CLICK) / 0.12)
    _cursor(cv, px, py, press)


CAPABILITY = Capability(
    id='bookmark-fill',
    name='Bookmark fill',
    family='ui',
    group='Toggles & controls',
    aliases=('save icon fill', 'favorite fill', 'bookmark toggle'),
    definition='Clicking an outlined bookmark icon floods it with colour from the bottom up, '
               'and it gives a small springy pop once it is solid to show the item is saved.',
    phrasings=('the save icon fills in with colour when I click it',
               'animate the bookmark button going from outline to solid with a little bounce',
               'a bookmark that fills up from below when something gets saved'),
    related=('icon-line-to-fill', 'outline-to-fill', 'stroke-draw-logo-loader', 'skeleton-shimmer',
             'ink-outline', 'bullet-graph-fill'),
    api=('videobuilder.capabilities.ui.bookmark_fill.bookmark_fill',
         'videobuilder.capabilities.ui.bookmark_fill.draw_bookmark',
         'videobuilder.capabilities.ui.bookmark_fill.saved_pop',
         'videobuilder.capabilities.ui.bookmark_fill.bookmark_path'),
    demo=lambda: demo.film(draw),
)
