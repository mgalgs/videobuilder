"""Small helpers the `ending_*` components share: beat timing from a shot,
fitting copy to a box by stepping the type size down, a soft ease, and
point-list drawing on raw cairo. Not a component (the leading underscore
keeps `components/__init__.py` from loading it as one)."""
import math

import videobuilder as vb
from videobuilder import text

from .. import kit


def fpb(shot):
    """Frames a beat for this shot: its own length over its own beats, so a
    recipe's tempo is honoured, not just the preview's 120 bpm."""
    beats = shot.segment.until - shot.segment.at
    return shot.length / beats if beats > 0 else kit.GRID.frames_per_beat


def smoother(t):
    """6t^5 - 15t^4 + 10t^3: starts and lands at rest."""
    t = vb.clamp01(t)
    return t * t * t * (t * (6 * t - 15) + 10)


def spring(f, ratio=0.55, hz=2.4):
    """A unit spring `f` frames after it starts (0 before)."""
    return vb.spring_at(f, 30, **vb.damped(ratio, hz=hz))


def fit(copy, sizes, weight, max_w, max_lines, family=None, **kw):
    """The largest size in `sizes` (descending) whose wrap of `copy` within
    `max_w` takes at most `max_lines` lines, as (font, lines, w, h). The
    smallest size is returned regardless, so the caller always gets a layout."""
    for size in sizes:
        f = vb.Font(family or kit.SANS, size, weight=weight, **kw)
        lines = text.wrap(copy, f, max_w, balance=True)
        if len(lines) <= max_lines:
            break
    w, h = text.block_size(lines, f) if lines else (0, 0)
    return f, lines, w, h


def poly(ctx, pts, closed=True):
    ctx.new_path()
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    if closed:
        ctx.close_path()


def fill_poly(cv, pts, color, alpha=1.0):
    poly(cv.ctx, pts)
    cv.ctx.set_source_rgba(*vb.rgba(color, alpha))
    cv.ctx.fill()


def bounds(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


def circle_pts(cx, cy, r, n=48, a0=0.0):
    return [(cx + r * math.cos(a0 + 2 * math.pi * i / n), cy + r * math.sin(a0 + 2 * math.pi * i / n))
            for i in range(n)]
