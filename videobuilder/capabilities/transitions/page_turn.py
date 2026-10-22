"""Page turn: the outgoing scene is a sheet of paper whose corner lifts and
folds back across the frame, its pale underside sweeping over it, until the
whole sheet has turned away and the incoming scene lies beneath."""
import math

import cairo

from .. import _demo as demo
from ...ease import bezier
from ..schema import Capability

_turn = bezier(0.5, 0, 0.3, 1)


def _cut(pts, n, c):
    """The part of polygon `pts` where n . X >= c (one Sutherland-Hodgman pass)."""
    out = []
    for i, p in enumerate(pts):
        q = pts[(i + 1) % len(pts)]
        dp, dq = n[0] * p[0] + n[1] * p[1] - c, n[0] * q[0] + n[1] * q[1] - c
        if dp >= 0:
            out.append(p)
        if (dp >= 0) != (dq >= 0):
            s = dp / (dp - dq)
            out.append((p[0] + (q[0] - p[0]) * s, p[1] + (q[1] - p[1]) * s))
    return out


def _path(ctx, pts):
    ctx.new_path()
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()


def page_turn(cv, a, b, p, corner='bottom-right', tilt=0.18, paper='#fdfcf8', shine=0.12):
    """Draw the page turn at progress `p` (0 -> 1): `a(cv)` is a sheet whose
    `corner` ('bottom-right', 'top-right', 'bottom-left', 'top-left') peels up
    and folds back over it, showing its paper-coloured underside (with `a`
    showing through faintly, at `shine`), until `b(cv)` lies fully revealed
    beneath. `tilt` (radians) turns the fold off the diagonal so it reads as a
    hand turning a page rather than a rigid flip. Progress is eased inside.

    In a film, call it inside an overlap, e.g.
    `page_turn(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    w, h = cv.width, cv.height
    page = [(0, 0), (w, 0), (w, h), (0, h)]
    sx = 1 if 'right' in corner else -1
    sy = 1 if 'bottom' in corner else -1
    cx, cy = (w if sx > 0 else 0), (h if sy > 0 else 0)
    # u points from the lifting corner into the page; the fold line is u . X = c.
    ang = math.atan2(-sy * h, -sx * w) + tilt * sx * sy
    u = (math.cos(ang), math.sin(ang))
    base = u[0] * cx + u[1] * cy
    reach = max(u[0] * x + u[1] * y for x, y in page) - base
    c = base + reach * _turn(max(0.0, min(1.0, p)))

    flat = _cut(page, u, c)                               # the part of `a` still lying flat
    lifted = _cut(page, (-u[0], -u[1]), -c)               # the part that has folded away
    nx, ny = u
    mirror = cairo.Matrix(1 - 2 * nx * nx, -2 * nx * ny, -2 * nx * ny, 1 - 2 * ny * ny, 2 * c * nx, 2 * c * ny)
    flap = [mirror.transform_point(*q) for q in lifted]   # where the folded part now lies, over `a`
    ctx = cv.ctx

    def gradient(depth, stops):
        g = cairo.LinearGradient(c * nx, c * ny, (c + depth) * nx, (c + depth) * ny)
        for off, alpha in stops:
            g.add_color_stop_rgba(off, 0, 0, 0, alpha)
        return g

    b(cv)
    if len(lifted) >= 3:  # the revealed scene darkens where the sheet still hangs over it
        ctx.save()
        _path(ctx, lifted)
        ctx.clip()
        ctx.set_source(gradient(-90, ((0, 0.45), (1, 0))))
        ctx.paint()
        ctx.restore()
    if len(flat) >= 3:
        ctx.save()
        _path(ctx, flat)
        ctx.clip()
        a(cv)
        if len(flap) >= 3:
            cv.shape_shadow(flap, dx=-sx * 10, dy=-sy * 8, blur=22, color=(0, 0, 0, 0.4))
        ctx.restore()
    if len(flap) >= 3:
        ctx.save()
        _path(ctx, flap)
        ctx.clip()
        cv.fill(paper)
        ctx.save()
        ctx.transform(mirror)
        with cv.layer(opacity=shine):
            a(cv)
        ctx.restore()
        # Shade the underside: dark in the crease, lifting to a soft sheen.
        ctx.set_source(gradient(220, ((0, 0.32), (0.25, 0.08), (0.6, 0), (1, 0.06))))
        ctx.paint()
        ctx.restore()
        _path(ctx, flap)
        ctx.set_source_rgba(0, 0, 0, 0.3)
        ctx.set_line_width(1.5)
        ctx.stroke()


CAPABILITY = Capability(
    id='page-turn',
    name='Page turn',
    family='transitions',
    group='Page and Fold',
    aliases=('page curl', 'page peel', 'page flip', 'book page turn'),
    definition='A corner of the current picture lifts like paper and folds back across the frame, '
               'its blank underside sweeping over it, until the sheet is gone and the next scene lies beneath.',
    phrasings=('turn the page to get to the next scene',
               'peel the shot away from the corner like a sheet of paper',
               'make it look like flipping to the next page of a book'),
    related=('word-flip-in', 'flip', 'layout-animation-flip', 'tile-flip', 'character-3d-flip',
             'logo-3d-spin-reveal'),
    api=('videobuilder.capabilities.transitions.page_turn.page_turn',),
    demo=lambda: demo.two_scenes(page_turn, start=0.6, length=1.8),
)
