"""Wave Deformer: a flat sheet seen in perspective is lifted and lowered by a
sine of its position, and the sine's phase advances with time, so a regular
wave rolls through the surface while the sheet itself stays put."""
import math

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Technique


def wave_height(u, v, t, amplitude=60.0, wavelength=420.0, speed=0.6, heading=0.0, phase=0.0):
    """The height of the wave at point (u, v) of a sheet, `t` seconds in:
    `amplitude * sin(2pi (d / wavelength - speed t) + phase)`, where `d` is
    the distance along `heading` degrees (0: along u, 90: along v). Crests
    travel `speed` cycles a second towards +heading."""
    a = math.radians(heading)
    d = u * math.cos(a) + v * math.sin(a)
    return amplitude * math.sin(2 * math.pi * (d / wavelength - speed * t) + phase)


def _slope(u, v, t, amplitude, wavelength, speed, heading, phase):
    """The height's gradient (dh/du, dh/dv) at (u, v)."""
    a = math.radians(heading)
    k = 2 * math.pi / wavelength
    d = u * math.cos(a) + v * math.sin(a)
    g = amplitude * k * math.cos(k * d - 2 * math.pi * speed * t + phase)
    return g * math.cos(a), g * math.sin(a)


def _shade(color, k):
    r, g, b, a = rgba(color)
    return (min(255, round(r * 255 * k)), min(255, round(g * 255 * k)), min(255, round(b * 255 * k)), a)


def wave_sheet(cv, cx, cy, width, depth, t, color, amplitude=60.0, wavelength=420.0, speed=0.6,
               heading=0.0, phase=0.0, tilt=28.0, yaw=0.0, distance=1800.0, cols=48, rows=18,
               grid=None, grid_alpha=0.35, alpha=1.0):
    """Draw a `width` x `depth` px sheet centred at (cx, cy), deformed by a
    travelling sine wave (`wave_height` with `amplitude`, `wavelength`,
    `speed`, `heading`, `phase`) at time `t` seconds. The sheet lies flat,
    turned `yaw` degrees about the vertical and viewed from `tilt` degrees
    above, in perspective (`distance` is the camera distance; smaller
    exaggerates it). It is cut into a `cols` x `rows` mesh, each cell lit by
    its slope so crests catch the light and troughs fall dark, with the mesh
    lines drawn in `grid` (default: `color` darkened). Returns the Box the
    flat sheet would cover on screen, for marks."""
    wave = dict(amplitude=amplitude, wavelength=wavelength, speed=speed, heading=heading, phase=phase)
    ya, ta = math.radians(yaw), math.radians(tilt)
    cy_, sy_ = math.cos(ya), math.sin(ya)
    ct, st = math.cos(ta), math.sin(ta)
    lx, ly, lz = -0.45, 0.8, -0.4  # light from above, a little left and in front
    ln = math.sqrt(lx * lx + ly * ly + lz * lz)
    lx, ly, lz = lx / ln, ly / ln, lz / ln

    def project(u, v, h):  # sheet (u right, v away, h up) -> screen, and depth
        x, z = u * cy_ - v * sy_, u * sy_ + v * cy_       # yaw about the vertical
        y, z = h * ct - z * st, h * st + z * ct            # tip the far edge up into view
        f = distance / (distance + z)
        return (cx + x * f, cy - y * f), z

    us = [-width / 2 + width * i / cols for i in range(cols + 1)]
    vs = [-depth / 2 + depth * j / rows for j in range(rows + 1)]
    pts = [[project(u, v, wave_height(u, v, t, **wave)) for u in us] for v in vs]

    cells = []
    for j in range(rows):
        for i in range(cols):
            corners = (pts[j][i], pts[j][i + 1], pts[j + 1][i + 1], pts[j + 1][i])
            z = sum(c[1] for c in corners) / 4
            gu, gv = _slope((us[i] + us[i + 1]) / 2, (vs[j] + vs[j + 1]) / 2, t, **wave)
            nx, nv, ny = -gu, -gv, 1.0                         # surface normal in sheet space
            nn = math.sqrt(nx * nx + nv * nv + ny * ny)
            wx, wz = nx * cy_ - nv * sy_, nx * sy_ + nv * cy_  # same yaw as the points
            lit = max(0.0, (wx * lx + ny * ly + wz * lz) / nn)
            cells.append((z, [c[0] for c in corners], 0.3 + 0.9 * lit ** 1.5))

    ctx = cv.ctx
    line = rgba(grid if grid is not None else _shade(color, 0.45), grid_alpha)
    with cv.layer(opacity=alpha):
        for _, quad, k in sorted(cells, key=lambda c: -c[0]):   # far cells first
            ctx.new_path()
            ctx.move_to(*quad[0])
            for x, y in quad[1:]:
                ctx.line_to(x, y)
            ctx.close_path()
            ctx.set_source_rgba(*rgba(_shade(color, k)))
            ctx.fill_preserve()
            ctx.set_source_rgba(*line)
            ctx.set_line_width(0.8)
            ctx.stroke()
    flat = [project(u, v, 0)[0] for u in (us[0], us[-1]) for v in (vs[0], vs[-1])]
    x0, x1 = min(p[0] for p in flat), max(p[0] for p in flat)
    y0, y1 = min(p[1] for p in flat) - amplitude, max(p[1] for p in flat) + amplitude
    return vb.Box(x0, y0, x1 - x0, y1 - y0)


def draw(n, cv):
    t = n / demo.FPS
    amp = 38 * vb.ease_in_out_quart(demo.phase(n, 0.15, 0.9))  # a flat sheet first, then the wave swells in
    yaw = -18 + 10 * math.sin(2 * math.pi * t / demo.SECONDS)  # a slow sway, so the sheet reads as 3D
    box = wave_sheet(cv, demo.W / 2, demo.H / 2 + 20, 600, 280, t, demo.TEAL, amplitude=amp,
                     wavelength=210, speed=0.7, tilt=32, yaw=yaw, distance=1100, cols=44, rows=16)
    cv.mark('sheet', *box)


TECHNIQUE = Technique(
    id='wave-deformer',
    name='Wave deformer',
    family='camera',
    group='3D motion',
    aliases=('sine deform', 'ripple deformer', 'wave deform'),
    definition='A flat 3D sheet is pushed up and down by a regular sine wave whose crests keep rolling '
               'across it, so the surface undulates in place like cloth or water.',
    phrasings=('make the plane ripple like a flag with waves running across it',
               'put a rolling sine wave through this 3D surface',
               'the grid should bend into waves that keep travelling along it'),
    related=('sine-wave-distortion', 'wave-stagger', 'ripple-displacement', 'height-field-ripples',
             'ripple', 'refraction-ripple'),
    api=('videobuilder.techniques.camera.wave_deformer.wave_sheet',
         'videobuilder.techniques.camera.wave_deformer.wave_height'),
    demo=lambda: demo.film(draw),
)
