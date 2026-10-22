"""Border glow follow: a card's outline stays dim except near the pointer,
where it lights up; the lit patch slides around the edge as the pointer moves."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

ARROW = ((0, 0), (0, 27), (7, 21), (12, 32), (17.5, 29.5), (12.5, 19), (21, 19))


def _rounded(ctx, x, y, w, h, r):
    r = max(0.0, min(r, w / 2, h / 2))
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()


def border_glow(cv, x, y, w, h, px, py, color, radius=18, reach=120, width=2, halo=10, strength=1.0):
    """Light the edge of the box (x, y, w, h) around the pointer at (px, py):
    a `width` px stroke in `color`, brightest nearest the pointer and gone
    `reach` px from it, over a softer `halo` px wide glow. Draw it on top of
    the card; the dim resting border is the card's own. A pointer further
    than `reach` from every edge lights nothing, so it fades in and out on
    its own as the pointer comes and goes. `strength` scales the whole glow."""
    c = cv.ctx
    r, g, b, a = vb.rgba(color)
    for line_w, peak in ((halo, 0.4), (halo * 0.45, 0.6), (width, 1.0)):
        grad = cairo.RadialGradient(px, py, 0, px, py, reach)
        grad.add_color_stop_rgba(0, r, g, b, a * peak * strength)
        grad.add_color_stop_rgba(0.5, r, g, b, a * peak * strength * 0.5)
        grad.add_color_stop_rgba(1, r, g, b, 0)
        c.save()
        c.new_path()
        _rounded(c, x, y, w, h, radius)
        c.set_source(grad)
        c.set_line_width(line_w)
        c.stroke()
        c.restore()


def _spline(points, t):
    """Catmull-Rom through `points` at `t` 0 -> 1, evenly timed per point."""
    k = min(int(t * (len(points) - 1)), len(points) - 2)
    u = t * (len(points) - 1) - k
    p0, p1, p2, p3 = (points[max(0, min(len(points) - 1, i))] for i in (k - 1, k, k + 1, k + 2))
    return tuple(0.5 * (2 * b + (c - a) * u + (2 * a - 5 * b + 4 * c - d) * u * u
                        + (3 * b - a - 3 * c + d) * u ** 3) for a, b, c, d in zip(p0, p1, p2, p3))


def _pointer(cv, x, y):
    pts = [(x + px * 0.85, y + py * 0.85) for px, py in ARROW]
    cv.shape_shadow(pts, dx=1, dy=2, blur=4, color=(0, 0, 0, 0.5))
    c = cv.ctx
    c.new_path()
    c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    c.close_path()
    c.set_source_rgba(*vb.rgba(demo.INK))
    c.fill_preserve()
    c.set_source_rgba(*vb.rgba(demo.BG))
    c.set_line_width(1.5)
    c.stroke()


def draw(n, cv):
    w, h, rad = 360, 210, 16
    x, y = (demo.W - w) / 2, (demo.H - h) / 2
    # the card: dark panel, faint resting border, placeholder text and a button
    cv.shadow(x, y, w, h, radius=rad, dy=8, blur=24, color=(0, 0, 0, 0.5))
    cv.rect(x, y, w, h, '#1c1e25', radius=rad)
    cv.outline(x, y, w, h, demo.LINE, width=2, radius=rad)
    for i, (bw, a) in enumerate(((0.42, 0.55), (0.72, 0.3), (0.6, 0.3))):
        cv.rect(x + 28, y + 30 + i * 20 + (8 if i else 0), w * bw, 8, demo.MUTED, radius=4, alpha=a)
    cv.rect(x + 28, y + h - 60, 88, 32, demo.TEAL, radius=8, alpha=0.85)
    cv.mark('card', x, y, w, h)
    # the pointer loops around the card just outside its edge, from off to the top right
    path = [(x + w + 200, y - 110), (x + w * 0.75, y - 4), (x + w + 4, y + h * 0.3),
            (x + w + 1, y + h + 1), (x + w * 0.3, y + h + 5), (x - 5, y + h * 0.55),
            (x + 1, y + 1), (x + w * 0.45, y - 110)]
    t = demo.phase(n, 0.2, 2.9)
    px, py = _spline(path, t * t * (3 - 2 * t))
    border_glow(cv, x, y, w, h, px, py, demo.TEAL, radius=rad)
    _pointer(cv, px, py)


CAPABILITY = Capability(
    id='border-glow-follow',
    name='Border glow follow',
    family='ui',
    group='Cursor & hover',
    aliases=('cursor border highlight', 'gradient border follow', 'spotlight border', 'mouse-tracking border glow'),
    definition='Only the stretch of a card\'s outline closest to the mouse pointer glows, and that bright '
               'patch slides around the edge to stay with the pointer as it moves.',
    phrasings=('the card edge lights up wherever the mouse is near it',
               'a glowing border that tracks the cursor around the card',
               'make the outline shine just next to the pointer as it moves around'),
    related=('outline-pulse-glow', 'fresnel-edge-glow', 'drop-target-highlight', 'highlighter-swipe',
             'gradient-border-spin', 'border-draw-button'),
    api=('videobuilder.capabilities.ui.border_glow_follow.border_glow',),
    demo=lambda: demo.film(draw),
)
