"""Magnetic field lines: curves loop out of one pole of a magnet and back
into the other, each one traced step by step along the direction a dipole
field points, so together they make the familiar iron-filings pattern."""
import math

import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ..schema import Capability


def _field(x, y, north, south):
    # a source at the north pole and a sink at the south, falling off as 1/r^2
    fx = fy = 0.0
    for (px, py), q in ((north, 1.0), (south, -1.0)):
        dx, dy = x - px, y - py
        d3 = max((dx * dx + dy * dy) ** 1.5, 1e-9)
        fx += q * dx / d3
        fy += q * dy / d3
    return fx, fy


def dipole_field_lines(north, south, count=16, spread=0.82, start=24.0, step=6.0, bounds=None,
                       max_steps=900):
    """The field lines between a `north` and a `south` pole (each `(x, y)`),
    as `count` polylines, each a list of `(x, y)` from the north pole to the
    south. Lines leave the north pole at angles fanned evenly across
    `spread` (a fraction of a half turn) either side of the line towards the
    south pole, starting `start` px out; each is traced in `step` px steps
    (midpoint rule) along the field until it comes within `start` px of the
    south pole, leaves `bounds` `(x0, y0, x1, y1)` (None: no limit) or runs
    `max_steps` steps. Pure geometry: trace once, draw every frame."""
    nx, ny = north
    sx, sy = south
    axis = math.atan2(sy - ny, sx - nx)
    lines = []
    for i in range(count):
        u = (i + 0.5) / count * 2 - 1 if count > 1 else 0.0
        a = axis + u * spread * math.pi
        x, y = nx + start * math.cos(a), ny + start * math.sin(a)
        pts = [(nx, ny), (x, y)]
        for _ in range(max_steps):
            fx, fy = _field(x, y, north, south)
            m = math.hypot(fx, fy) or 1.0
            mx, my = x + fx / m * step / 2, y + fy / m * step / 2
            fx, fy = _field(mx, my, north, south)
            m = math.hypot(fx, fy) or 1.0
            x, y = x + fx / m * step, y + fy / m * step
            pts.append((x, y))
            if math.hypot(x - sx, y - sy) < start:
                pts.append((sx, sy))
                break
            if bounds and not (bounds[0] <= x <= bounds[2] and bounds[1] <= y <= bounds[3]):
                break
        lines.append(pts)
    return lines


def _lengths(pts):
    out = [0.0]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        out.append(out[-1] + math.hypot(x1 - x0, y1 - y0))
    return out


def _point_at(pts, acc, s):
    for k in range(1, len(pts)):
        if acc[k] >= s:
            t = (s - acc[k - 1]) / max(acc[k] - acc[k - 1], 1e-9)
            (x0, y0), (x1, y1) = pts[k - 1], pts[k]
            return x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
    return pts[-1]


def draw_field_lines(cv, lines, progress=1.0, flow=None, north_color=demo.ACCENT, south_color=demo.TEAL,
                     width=2.0, alpha=0.85, bead_gap=90.0, bead_r=3.5):
    """Draw `lines` (from `dipole_field_lines`) onto `cv`, each shaded from
    `north_color` at its start to `south_color` at its end. `progress`
    (0 -> 1) draws every line on from the north pole, all arriving together.
    `flow` (None: off) is a distance in px: beads spaced `bead_gap` apart ride
    along the drawn part of each line, shifted by `flow`, so advancing it
    every frame shows the field's direction."""
    progress = vb.clamp01(progress)
    if progress <= 0:
        return
    for pts in lines:
        acc = _lengths(pts)
        total = acc[-1]
        reach = total * progress
        for k in range(1, len(pts)):
            if acc[k - 1] >= reach:
                break
            (x0, y0), (x1, y1) = pts[k - 1], pts[k]
            if acc[k] > reach:
                t = (reach - acc[k - 1]) / max(acc[k] - acc[k - 1], 1e-9)
                x1, y1 = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            c = kit.mix(north_color, south_color, acc[k] / max(total, 1e-9))
            cv.line(x0, y0, x1, y1, c, width=width, alpha=alpha)
        if flow is not None and bead_gap > 0:
            s = flow % bead_gap
            while s < reach:
                bx, by = _point_at(pts, acc, s)
                demo.dot(cv, bx, by, bead_r, color=kit.mix(north_color, south_color, s / max(total, 1e-9)))
                s += bead_gap


_LINES = {}


def _demo_lines():
    if 'lines' not in _LINES:
        _LINES['lines'] = dipole_field_lines(_NORTH, _SOUTH, count=20, spread=0.55, start=16, step=3,
                                             bounds=(0, 0, demo.W, demo.H))
    return _LINES['lines']


_NORTH, _SOUTH = (demo.W / 2 - 130, demo.H / 2), (demo.W / 2 + 130, demo.H / 2)


def draw(n, cv):
    grow = demo.phase(n, 0.2, 1.7)
    grow = 1 - (1 - grow) ** 3
    t = n / demo.FPS
    flow = 70 * (t - 1.2) if t > 1.2 else None
    draw_field_lines(cv, _demo_lines(), grow, flow=flow, width=1.6, bead_gap=48, bead_r=2.4)
    for (x, y), c, label in ((_NORTH, demo.ACCENT, 'N'), (_SOUTH, demo.TEAL, 'S')):
        demo.dot(cv, x, y, 17, color=c)
        demo.word(cv, label, x, y, size=18, color=demo.BG)
        cv.mark(label, x - 17, y - 17, 34, 34)


CAPABILITY = Capability(
    id='magnetic-field-lines',
    name='Magnetic field lines',
    family='particles',
    group='Noise & fields',
    aliases=('dipole field lines', 'magnet lines', 'iron filings pattern'),
    definition='Curved strands sweep out of one magnetic pole and bend round into the other, '
               'each following the pull of the field, so they draw the classic looping pattern of a bar magnet.',
    phrasings=('show the field lines looping between two magnet poles',
               'draw those curved lines that go from north to south like iron filings',
               'animate a magnetic field arcing from one pole to the other'),
    related=('sparkline-draw', 'speed-lines', 'line-weave', 'line-chart-draw-on', 'flow-map-lines',
             'virtual-first-down-line'),
    api=('videobuilder.capabilities.particles.magnetic_field_lines.dipole_field_lines',
         'videobuilder.capabilities.particles.magnetic_field_lines.draw_field_lines'),
    demo=lambda: demo.film(draw),
)
