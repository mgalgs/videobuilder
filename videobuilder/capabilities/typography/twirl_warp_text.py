"""Twirl Warp Text: the same twist as Swirl (`swirl.py`, which keeps the
capability) -- both spiral warp something about its centre, hardest in the
middle and easing off toward the edge, and both unwind flat: here a word's
outlines are spun that way, there a whole scene. This module's own code
stays (a film may still import it), but it is no longer a capability of its
own."""
import math

import videobuilder as vb
from gi.repository import PangoCairo

from ... import text as vbtext
from .. import _demo as demo

MERGED_INTO = 'swirl'


def twirl(x, y, cx, cy, angle, radius):
    """(x, y) turned about (cx, cy) by `angle` radians at the centre, falling
    smoothly to no turn at distance `radius` and beyond."""
    dx, dy = x - cx, y - cy
    d = math.hypot(dx, dy)
    if d >= radius or not angle:
        return x, y
    t = 1 - d / radius
    a = angle * t * t
    c, s = math.cos(a), math.sin(a)
    return cx + dx * c - dy * s, cy + dx * s + dy * c


def _flat_contours(ctx, step):
    """The current path as closed polygons, its straight runs cut into
    pieces no longer than `step` px so they bend when warped."""
    out, pts = [], []
    for kind, p in ctx.copy_path_flat():
        if kind == 0:  # MOVE_TO
            if len(pts) > 2:
                out.append(pts)
            pts = [p]
        elif kind == 1:  # LINE_TO
            (x0, y0), (x1, y1) = pts[-1], p
            k = max(1, math.ceil(math.hypot(x1 - x0, y1 - y0) / step))
            pts.extend((x0 + (x1 - x0) * i / k, y0 + (y1 - y0) * i / k) for i in range(1, k + 1))
    if len(pts) > 2:
        out.append(pts)
    return out


def draw_twirl(cv, text, font, cx, cy, angle, color, radius=None, center=None, alpha=1.0, step=4.0):
    """Draw one line of `text` centred at (cx, cy), its outlines twirled by
    `angle` radians about `center` (default the line's centre) with the turn
    fading out at `radius` (default 0.6 x the line's width). Animate `angle`
    to 0 for the twirl to unwind into plain text. Returns the Box the plain
    line takes up."""
    w, h = vbtext.block_size([text], font)
    x, y = cx - w / 2, cy - h / 2
    ox, oy = center or (cx, cy)
    radius = radius or 0.6 * w
    ctx = cv.ctx
    ctx.save()
    ctx.new_path()
    ctx.set_tolerance(0.25)
    ctx.move_to(x, y + (h - vbtext._content(font)[0]) / 2)
    PangoCairo.layout_path(ctx, vbtext._layout(ctx, text, font))
    contours = _flat_contours(ctx, step)
    ctx.new_path()
    for pts in contours:
        ctx.move_to(*twirl(*pts[0], ox, oy, angle, radius))
        for p in pts[1:]:
            ctx.line_to(*twirl(*p, ox, oy, angle, radius))
        ctx.close_path()
    ctx.set_source_rgba(*vb.canvas.rgba(color, alpha))
    ctx.fill()
    ctx.restore()
    return vb.Box(x, y, w, h)


def draw(n, cv):
    p = demo.phase(n, 0.5, 2.8)
    angle = 3.5 * math.pi * (1 - p * p * (3 - 2 * p))  # smoothstep: hold the spiral, linger mid-twist, settle flat
    text, font = 'WHIRLPOOL', demo.font(84, 900)
    # a turn never changes a point's distance from the centre, so a radius
    # under half the frame height keeps every arm of the spiral in frame
    radius = min(0.6 * vbtext.block_size([text], font)[0], demo.H / 2 - 24)
    box = draw_twirl(cv, text, font, demo.W / 2, demo.H / 2, angle, demo.INK, radius=radius)
    cv.mark('text', *box)
