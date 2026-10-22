"""3D Tilt on Hover: a flat card turns in perspective to follow the pointer
over it -- the side under the cursor presses away, a soft glare tracks the
pointer -- and settles flat again when the pointer leaves."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def tilt_angles(px, py, cx, cy, w, h, max_deg=14.0, hover=1.0):
    """The card's tilt `(ax, ay)` in radians for a pointer at (px, py) over a
    card `w` x `h` centred at (cx, cy): about the horizontal axis, then the
    vertical one. The point under the pointer presses away from the viewer,
    up to `max_deg` at an edge (a negative `max_deg` lifts it towards the
    viewer instead). `hover` (0 -> 1) scales the whole tilt, so easing it
    in and out lets the card settle flat when the pointer leaves."""
    nx = max(-1.0, min(1.0, (px - cx) / (w / 2)))
    ny = max(-1.0, min(1.0, (py - cy) / (h / 2)))
    k = math.radians(max_deg) * vb.clamp01(hover)
    return ny * k, nx * k


def project(u, v, cx, cy, ax, ay, scale=1.0, distance=900.0):
    """Screen point of the card-local point (u, v) (px from the card's centre,
    y down) on a card centred at (cx, cy), tilted by `(ax, ay)` and seen
    from `distance` px in front. Also returns its depth (+ is towards the viewer)."""
    u, v = u * scale, v * scale
    x1, z1 = u * math.cos(ay), -u * math.sin(ay)
    y2, z2 = v * math.cos(ax) + z1 * math.sin(ax), -v * math.sin(ax) + z1 * math.cos(ax)
    s = distance / (distance - z2)
    return (cx + x1 * s, cy + y2 * s), z2


def _rounded(x, y, w, h, r, steps=6):
    """The outline of a rounded box as a point list (card-local px)."""
    r = min(r, w / 2, h / 2)
    pts = []
    for ccx, ccy, a0 in ((x + w - r, y + r, -math.pi / 2), (x + w - r, y + h - r, 0),
                         (x + r, y + h - r, math.pi / 2), (x + r, y + r, math.pi)):
        for i in range(steps + 1):
            a = a0 + (math.pi / 2) * i / steps
            pts.append((ccx + r * math.cos(a), ccy + r * math.sin(a)))
    return pts


def _path(ctx, pts):
    ctx.new_path()
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()


def draw_tilt_card(cv, cx, cy, w, h, ax, ay, color=demo.ACCENT, glare=None, lift=0.0, radius=18,
                   distance=900.0, ink=demo.INK):
    """Draw a UI card `w` x `h` centred at (cx, cy) tilted by `(ax, ay)` (from
    `tilt_angles`) in perspective: a shadow that drifts away from the
    pressed side, the panel, two text bars, and a soft glare at the screen
    point `glare` (the pointer; `None` for none). `lift` (0 -> 1) raises the
    card a little off the page, as hover does. Returns the Box it covers."""
    scale = 1 + 0.05 * lift
    to_screen = lambda pts: [project(u, v, cx, cy, ax, ay, scale, distance)[0] for u, v in pts]  # noqa: E731
    face = to_screen(_rounded(-w / 2, -h / 2, w, h, radius))
    xs, ys = [p[0] for p in face], [p[1] for p in face]
    bw, bh = max(xs) - min(xs), max(ys) - min(ys)
    sx, sy = math.sin(ay) * 40, math.sin(ax) * 40
    cv.shadow(min(xs) - sx, min(ys) - sy, bw, bh, radius=radius, dy=10 + 14 * lift, blur=28 + 18 * lift,
              color=(0, 0, 0, 0.45 + 0.15 * lift))
    ctx = cv.ctx
    _path(ctx, face)
    ctx.set_source_rgba(*vb.rgba(color))
    ctx.fill()
    bar = h * 0.12
    for frac, alpha in ((0.62, 0.95), (0.4, 0.6)):
        top = -h / 2 + h * 0.3 + (0 if alpha > 0.9 else bar * 2)
        _path(ctx, to_screen(_rounded(-w / 2 + w * 0.12, top, w * frac, bar, bar / 2, 4)))
        ctx.set_source_rgba(*vb.rgba(ink, alpha))
        ctx.fill()
    if glare is not None:
        ctx.save()
        _path(ctx, face)
        ctx.clip()
        g = cairo.RadialGradient(glare[0], glare[1], 0, glare[0], glare[1], max(bw, bh) * 0.7)
        g.add_color_stop_rgba(0, 1, 1, 1, 0.35 * min(1.0, lift + 0.3))
        g.add_color_stop_rgba(1, 1, 1, 1, 0)
        ctx.set_source(g)
        ctx.paint()
        ctx.restore()
    # The lit and shaded rims: the edge nearer the viewer catches light.
    _path(ctx, face)
    ctx.set_source_rgba(1, 1, 1, 0.12 + 0.5 * abs(math.sin(ax)) + 0.5 * abs(math.sin(ay)))
    ctx.set_line_width(1.5)
    ctx.stroke()
    return vb.Box(min(xs), min(ys), bw, bh)


def pointer(cv, x, y, size=26, color=demo.INK):
    """A mouse-pointer arrow with its tip at (x, y)."""
    s = size / 26
    pts = [(0, 0), (0, 22), (6, 17), (10, 26), (14, 24), (10, 16), (17, 16)]
    pts = [(x + px * s, y + py * s) for px, py in pts]
    cv.shape_shadow(pts, dy=2, blur=4, color=(0, 0, 0, 0.5))
    _path(cv.ctx, pts)
    cv.ctx.set_source_rgba(*vb.rgba(color))
    cv.ctx.fill_preserve()
    cv.ctx.set_source_rgba(*vb.rgba(demo.BG))
    cv.ctx.set_line_width(1.5 * s)
    cv.ctx.stroke()


CX, CY, CW, CH = demo.W / 2, demo.H / 2, 360, 230
# Where the pointer is (seconds, x, y): in from the lower left, a lap of the card's corners, out to the right.
PATH = ((0.0, 150, 500), (0.55, CX - 110, CY + 60), (0.95, CX - 150, CY - 95), (1.45, CX + 150, CY - 95),
        (1.95, CX + 150, CY + 95), (2.3, CX, CY + 20), (2.95, 860, 470))


def _at(t):
    ts = [p[0] for p in PATH]
    ease = vb.bezier(0.45, 0, 0.55, 1)
    return (vb.interpolate(t, ts, [p[1] for p in PATH], ease=ease),
            vb.interpolate(t, ts, [p[2] for p in PATH], ease=ease))


def draw(n, cv):
    t = n / demo.FPS
    px, py = _at(t)
    hover = vb.ease_out_quint(demo.phase(n, 0.35, 0.75)) * (1 - vb.ease_in_out_quart(demo.phase(n, 2.3, 2.8)))
    ax, ay = tilt_angles(px, py, CX, CY, CW, CH, max_deg=16, hover=hover)
    box = draw_tilt_card(cv, CX, CY, CW, CH, ax, ay, glare=(px, py) if hover > 0 else None, lift=hover)
    cv.mark('card', *box)
    pointer(cv, px, py)


CAPABILITY = Capability(
    id='three-d-tilt-on-hover',
    name='3D tilt on hover',
    family='ui',
    group='Cursor & hover',
    aliases=('hover tilt', 'tilt card', 'parallax tilt card', 'perspective hover'),
    definition='A card leans in perspective towards wherever the pointer sits on it, with a glint '
               'following the pointer, and eases back flat once the pointer moves off.',
    phrasings=('the card tilts in 3D to follow my mouse when I hover over it',
               'make the panel lean toward the cursor like it is being pressed',
               'a hover effect where the card rotates with the pointer and catches the light'),
    related=('tilt', 'character-3d-flip', 'pedestal', 'cube-rotate', 'three-d-word-cube', 'flip'),
    api=('videobuilder.capabilities.ui.three_d_tilt_on_hover.draw_tilt_card',
         'videobuilder.capabilities.ui.three_d_tilt_on_hover.tilt_angles',
         'videobuilder.capabilities.ui.three_d_tilt_on_hover.project',
         'videobuilder.capabilities.ui.three_d_tilt_on_hover.pointer'),
    demo=lambda: demo.film(draw),
)
