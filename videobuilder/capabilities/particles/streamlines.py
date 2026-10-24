"""Streamlines: the same idea as Flow field (`flow_field.py`), which keeps
the capability -- both are curves following a hidden direction field, and
both alias "flow lines". This module's own code stays (a film may still
import it), but it is no longer a capability of its own."""
import math

import videobuilder as vb

from .. import _demo as demo

MERGED_INTO = 'flow-field'


def trace(field, x, y, step=6.0, steps=400, bounds=None):
    """The streamline through (x, y): a point list following `field(x, y) ->
    (vx, vy)` downstream in `step`-px hops (midpoint / RK2 integration on the
    unit direction, so line spacing doesn't depend on flow speed). Stops after
    `steps` hops, where the field goes still, or on leaving `bounds`
    `(x0, y0, x1, y1)` when given."""
    def unit(px, py):
        vx, vy = field(px, py)
        d = math.hypot(vx, vy)
        return (vx / d, vy / d) if d > 1e-9 else None

    pts = [(x, y)]
    for _ in range(steps):
        a = unit(x, y)
        if a is None:
            break
        b = unit(x + a[0] * step / 2, y + a[1] * step / 2)
        if b is None:
            break
        x, y = x + b[0] * step, y + b[1] * step
        if bounds and not (bounds[0] <= x <= bounds[2] and bounds[1] <= y <= bounds[3]):
            break
        pts.append((x, y))
    return pts


def streamlines(field, seeds, step=6.0, steps=400, bounds=None):
    """One `trace` per seed `(x, y)` in `seeds`, as a list of point lists."""
    return [trace(field, x, y, step, steps, bounds) for x, y in seeds]


def _point_at(points, s):
    """Position and unit direction at arc length `s` along `points`."""
    acc = 0.0
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        hop = math.hypot(x1 - x0, y1 - y0)
        if hop > 0 and acc + hop >= s:
            t = (s - acc) / hop
            return (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t), ((x1 - x0) / hop, (y1 - y0) / hop)
        acc += hop
    return None, None


def arrow(cv, x, y, dx, dy, color, size=9.0, alpha=1.0):
    """A small filled arrowhead at (x, y) pointing along the unit (dx, dy)."""
    c = cv.ctx
    nx, ny = -dy, dx
    c.new_path()
    c.move_to(x + dx * size, y + dy * size)
    c.line_to(x - dx * size * 0.6 + nx * size * 0.55, y - dy * size * 0.6 + ny * size * 0.55)
    c.line_to(x - dx * size * 0.6 - nx * size * 0.55, y - dy * size * 0.6 - ny * size * 0.55)
    c.close_path()
    c.set_source_rgba(*vb.canvas.rgba(color, alpha))
    c.fill()


def draw_streamlines(cv, lines, colors, width=1.6, progress=1.0, flow=None, spacing=160.0, arrow_size=8.0,
                     alpha=0.9, arrow_alpha=1.0):
    """Draw traced `lines` onto `cv`, line `i` in `colors[i % len(colors)]`.
    `progress` (0 -> 1) draws every line on from its seed by arc length.
    `flow`, when given, is a distance in px: arrowheads sit every `spacing`
    px along each drawn line, offset by `flow`, so animating `flow` upward
    makes them travel downstream; `arrow_alpha` fades them on their own."""
    for i, pts in enumerate(lines):
        color = colors[i % len(colors)]
        shown = vb.paths.reveal(pts, progress)
        vb.paths.draw(cv, shown, color, width=width, alpha=alpha)
        if flow is None or arrow_alpha <= 0 or len(shown) < 2:
            continue
        total = vb.paths.length(shown)
        s = (flow + i * spacing * 0.37) % spacing  # stagger lines so arrows don't stack into a column
        while s < total:
            p, d = _point_at(shown, s)
            if p:
                arrow(cv, p[0], p[1], d[0], d[1], color, arrow_size, arrow_alpha)
            s += spacing


# The demo field: steady flow from left to right parting round a round obstacle (ideal flow past a
# cylinder): the lines bunch up as they squeeze past it and close again behind.
CX, CY, R = demo.W * 0.5, demo.H * 0.5, demo.H * 0.13


def field(x, y):
    dx, dy = x - CX, y - CY
    r2 = dx * dx + dy * dy
    if r2 < R * R:
        return 0.0, 0.0
    k = R * R / (r2 * r2)
    vx = 1 - k * (dx * dx - dy * dy)
    vy = -2 * k * dx * dy
    return vx, vy


MARGIN = 40
BOUNDS = (MARGIN - 1, 10, demo.W - MARGIN + 1, demo.H - 10)  # outer lines may swing past the margin
SEEDS = [(MARGIN, CY + (i - 12.5) * 17) for i in range(26)]  # none on the centre line, which stalls
COLORS = (demo.TEAL, demo.INK, demo.TEAL, demo.ACCENT)
_LINES = []


def _lines():
    if not _LINES:
        _LINES.extend(streamlines(field, SEEDS, step=3.0, steps=600, bounds=BOUNDS))
    return _LINES


def draw(n, cv):
    grow = demo.phase(n, 0.1, 1.6)
    grow = 1 - (1 - grow) ** 3
    arrows = demo.phase(n, 0.9, 1.3)
    t = n / demo.FPS
    demo.dot(cv, CX, CY, R - 6, color=demo.LINE, alpha=0.6)
    draw_streamlines(cv, _lines(), COLORS, width=1.3, progress=grow, flow=t * 70.0, spacing=110.0,
                     arrow_size=4.5, alpha=0.85, arrow_alpha=arrows)
    cv.mark('field', MARGIN, MARGIN, demo.W - 2 * MARGIN, demo.H - 2 * MARGIN)
