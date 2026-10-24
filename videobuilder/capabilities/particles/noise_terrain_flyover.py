"""Noise Terrain Flyover: the same noise-height wireframe grid streaming
toward a low camera as Wireframe terrain (`wireframe_terrain.py`, which
keeps the capability); they share the alias synthwave grid. This module's
own code stays (a film may still import it), but it is no longer a
capability of its own."""
import math

import cairo

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..typography.noise_field_warp import Noise

MERGED_INTO = 'wireframe-terrain'

_noises = {}


def terrain_height(x, z, seed=0, size=6.0, octaves=4):
    """Ground height in about [-1, 1] at world point (x, z): `octaves` layers
    of gradient noise with features about `size` world units across."""
    if seed not in _noises:
        _noises[seed] = Noise(f'terrain:{seed}')
    return _noises[seed].fbm(x / size, z / size, octaves)


def draw_terrain(cv, travel, x=0.0, y=0.0, w=None, h=None, seed=0, horizon=0.38, eye=2.6, relief=2.2,
                 cols=56, rows=30, cell=1.0, line=demo.TEAL, peak=demo.ACCENT, ground=demo.BG,
                 haze=None, width=1.6, octaves=4, size=6.0):
    """Draw the noise terrain inside the box (x, y, w, h) (default: the whole
    canvas) as seen from a camera `travel` world units along its flight.

    The camera sits `eye` units above sea level looking at the horizon, a
    `horizon` fraction of the way down the box; the ground is a grid of
    `cols` x `rows` cells `cell` units square, heights from `terrain_height`
    scaled by `relief`. Cells are drawn far to near, each filled with
    `ground` and edged with `line` (shading to `peak` on high ground), fading
    into `haze` (default `ground`) in the distance. Animate `travel` to fly;
    the grid scrolls through the noise, so any speed or easing works."""
    w = cv.width if w is None else w
    h = cv.height if h is None else h
    haze = ground if haze is None else haze
    cx, hy, focal = x + w / 2, y + h * horizon, w * 0.55
    far = rows * cell
    k0 = math.floor(travel / cell)
    half = cols // 2

    def project(wx, wz):
        d = wz - travel
        wy = relief * terrain_height(wx, wz, seed, size, octaves)
        return cx + focal * wx / d, hy + focal * (eye - wy) / d, wy

    # rows of grid points, nearest first, starting just ahead of the camera
    grid = []
    for k in range(k0 + 1, k0 + rows + 2):
        wz = k * cell
        grid.append((wz - travel, [project(i * cell, wz) for i in range(-half, half + 1)]))
    lc, pc, gc, zc = rgba(line), rgba(peak), rgba(ground), rgba(haze)
    ctx = cv.ctx
    ctx.save()
    ctx.rectangle(x, y, w, h)
    ctx.clip()
    ctx.set_line_width(width)
    ctx.set_line_join(1)  # round
    for r in range(len(grid) - 2, -1, -1):
        (d0, near), (d1, back) = grid[r], grid[r + 1]
        fog = vb.clamp01((d1 - far * 0.45) / (far * 0.55))  # 0 near, 1 at the far edge
        for i in range(len(near) - 1):
            quad = (near[i], near[i + 1], back[i + 1], back[i])
            ctx.move_to(quad[0][0], quad[0][1])
            for px, py, _ in quad[1:]:
                ctx.line_to(px, py)
            ctx.close_path()
            ctx.set_source_rgba(*_mix(gc, zc, fog))
            ctx.fill_preserve()
            hi = vb.clamp01((sum(q[2] for q in quad) / 4 / relief + 0.15) / 0.6)
            ctx.set_source_rgba(*_mix(_mix(lc, pc, hi), zc, fog))
            ctx.stroke()
    ctx.restore()


def _mix(a, b, t):
    return tuple(p + (q - p) * t for p, q in zip(a, b))


def draw(n, cv):
    t = n / demo.FPS
    sky = cv.ctx
    hy = demo.H * 0.38
    grad = cairo.LinearGradient(0, 0, 0, hy)
    grad.add_color_stop_rgba(0, *rgba(demo.BG))
    grad.add_color_stop_rgba(1, *rgba('#3a2430'))
    sky.rectangle(0, 0, demo.W, hy)
    sky.set_source(grad)
    sky.fill()
    cv.rect(0, hy, demo.W, 120, '#3a2430')  # haze behind the farthest ridges
    demo.dot(cv, demo.W / 2, hy - 40, 120, color=demo.ACCENT, alpha=0.85)
    draw_terrain(cv, travel=3.0 + 4.2 * t, seed=3, haze='#3a2430')
    cv.mark('terrain', 0, hy, demo.W, demo.H - hy)
