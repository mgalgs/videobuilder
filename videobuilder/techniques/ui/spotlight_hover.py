"""Spotlight Hover: a soft pool of light sits under the pointer inside a dark
card, lighting its surface and the nearby stretch of its border, and follows
the pointer as it moves; it fades out when the pointer leaves the card."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def _rounded(ctx, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    ctx.new_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()


def _pool(cx, cy, r, color, alpha):
    g = cairo.RadialGradient(cx, cy, 0, cx, cy, r)
    cr, cg, cb, _ = vb.rgba(color)
    g.add_color_stop_rgba(0, cr, cg, cb, alpha)
    g.add_color_stop_rgba(0.5, cr, cg, cb, alpha * 0.35)
    g.add_color_stop_rgba(1, cr, cg, cb, 0)
    return g


def spotlight(cv, box, x, y, strength=1.0, color='#ffffff', radius=170, corner=18, fill=0.2, edge=0.9,
              border=2):
    """Light the card `box` (x, y, w, h) from the pointer at (x, y): a radial
    pool of `color` at `fill` opacity on the surface, and a brighter one at
    `edge` opacity on its `border`-px rim, both `radius` px wide and clipped to
    the card's rounded corners (`corner`). `strength` (0 -> 1) scales both, so
    a film fades it in as the pointer enters and out as it leaves. Draw it
    over the card's surface and under its content."""
    if strength <= 0:
        return
    bx, by, bw, bh = box
    ctx = cv.ctx
    ctx.save()
    _rounded(ctx, bx, by, bw, bh, corner)
    ctx.clip()
    ctx.set_source(_pool(x, y, radius, color, fill * strength))
    ctx.paint()
    _rounded(ctx, bx + border / 2, by + border / 2, bw - border, bh - border, corner - border / 2)
    ctx.set_source(_pool(x, y, radius, color, edge * strength))
    ctx.set_line_width(border)
    ctx.stroke()
    ctx.restore()


def pointer(cv, x, y, size=26, color=demo.INK, outline=demo.BG):
    """A plain arrow pointer with its tip at (x, y)."""
    s = size / 34
    pts = [(0, 0), (0, 30), (8, 23), (13, 34), (18, 32), (13, 21), (23, 21)]
    ctx = cv.ctx
    ctx.new_path()
    for i, (px, py) in enumerate(pts):
        (ctx.move_to if i == 0 else ctx.line_to)(x + px * s, y + py * s)
    ctx.close_path()
    ctx.set_source_rgba(*vb.rgba(color))
    ctx.fill_preserve()
    ctx.set_source_rgba(*vb.rgba(outline))
    ctx.set_line_width(2 * s)
    ctx.stroke()


CW, CH, GAP = 250, 180, 30
SURFACE, RIM = '#1b1d24', '#2c2f3a'


def _path(t):
    """The demo pointer at `t` seconds: up through the left card, a loop
    around the middle one, then out across the right card's top corner."""
    pts = [(0.0, (150, 470)), (0.5, (230, 300)), (1.0, (400, 210)), (1.5, (560, 330)),
           (2.0, (420, 340)), (2.5, (760, 230)), (3.0, (930, 120))]
    for (t0, a), (t1, b) in zip(pts, pts[1:]):
        if t <= t1:
            u = vb.clamp01((t - t0) / (t1 - t0))
            u = u * u * (3 - 2 * u)
            return a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u
    return pts[-1][1]


def _inside(box, x, y, feather=40):
    """0 -> 1 as (x, y) goes from `feather` px outside the box to its edge."""
    bx, by, bw, bh = box
    dx = max(bx - x, 0, x - (bx + bw))
    dy = max(by - y, 0, y - (by + bh))
    return vb.clamp01(1 - math.hypot(dx, dy) / feather)


def draw(n, cv):
    mx, my = _path(n / demo.FPS)
    x0 = (demo.W - 3 * CW - 2 * GAP) / 2
    for i in range(3):
        box = (x0 + i * (CW + GAP), (demo.H - CH) / 2, CW, CH)
        bx, by, bw, bh = box
        cv.shadow(bx, by, bw, bh, radius=18, dy=8, blur=22, color=(0, 0, 0, 0.45))
        cv.rect(bx, by, bw, bh, SURFACE, radius=18)
        cv.outline(bx + 1, by + 1, bw - 2, bh - 2, RIM, width=2, radius=17)
        spotlight(cv, box, mx, my, strength=_inside(box, mx, my), radius=170)
        cv.rect(bx + 26, by + 30, 40, 40, demo.ACCENT, radius=10)
        cv.rect(bx + 26, by + 96, bw * 0.62, 13, demo.INK, radius=6.5, alpha=0.9)
        cv.rect(bx + 26, by + 122, bw * 0.42, 13, demo.INK, radius=6.5, alpha=0.45)
        cv.mark('card', *box)
    pointer(cv, mx, my)


TECHNIQUE = Technique(
    id='spotlight-hover',
    name='Spotlight hover',
    family='ui',
    group='Cursor & hover',
    aliases=('spotlight card', 'cursor glow', 'hover spotlight', 'mouse-follow glow'),
    definition='A soft circle of light tracks the pointer across a dark card, brightening the surface '
               'and the edge nearest it, and fades away when the pointer moves off.',
    phrasings=('a glow follows the mouse around inside the card',
               'when you hover a card it lights up right where the cursor is',
               'the card border catches the light near the pointer'),
    related=('spotlight-dim', 'spotlight-follow', 'shine-glint-sweep', 'highlighter-swipe', 'glow-button',
             'star-rating-fill'),
    api=('videobuilder.techniques.ui.spotlight_hover.spotlight',
         'videobuilder.techniques.ui.spotlight_hover.pointer'),
    demo=lambda: demo.film(draw),
)
