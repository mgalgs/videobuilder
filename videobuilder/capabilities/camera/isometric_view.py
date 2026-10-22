"""Isometric View: the scene is shown through an orthographic camera turned
45 degrees about the vertical and tipped down about 35.26 degrees, so the
three axes sit 120 degrees apart on screen, each shortened by the same
amount, and parallel edges never converge. The demo swings the camera from
a flat plan view into that angle, so a grid of tiles turns into blocks."""
import math

import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ...looks import kit as looks
from ..schema import Capability

ISO_YAW = math.pi / 4                         # 45 degrees about the vertical
ISO_ELEVATION = math.asin(math.tan(math.pi / 6))  # about 35.26 degrees down: the true isometric angle
PLAN = (0.0, math.pi / 2)                     # (yaw, elevation) of a straight-down plan view


def ortho_point(x, y, z, cx, cy, yaw=ISO_YAW, elevation=ISO_ELEVATION, scale=1.0):
    """World point (x, y, z) -- y up, +z toward the viewer before any turn --
    seen by an orthographic camera turned `yaw` radians about the vertical
    and looking down at `elevation` radians (pi/2 is straight down, 0 is
    level). The world origin lands at screen (cx, cy). The defaults give a
    true isometric view. Returns (screen x, screen y, depth), depth growing
    toward the viewer, for back-to-front sorting."""
    c, s = math.cos(yaw), math.sin(yaw)
    xr, zr = x * c - z * s, x * s + z * c
    ce, se = math.cos(elevation), math.sin(elevation)
    return cx + scale * xr, cy + scale * (zr * se - y * ce), zr * ce + y * se


def to_isometric(p, start=PLAN, ease=vb.ease_in_out_quart):
    """Camera (yaw, elevation) at progress `p` (0 -> 1) of a move from
    `start` into the isometric angle; pass both to `ortho_point`."""
    q = ease(vb.clamp01(p))
    return start[0] + (ISO_YAW - start[0]) * q, start[1] + (ISO_ELEVATION - start[1]) * q


# (outward normal, corner signs) of each box face, corners in winding order
FACES = (((0, 1, 0), ((-1, 1, -1), (1, 1, -1), (1, 1, 1), (-1, 1, 1))),
         ((1, 0, 0), ((1, -1, -1), (1, -1, 1), (1, 1, 1), (1, 1, -1))),
         ((-1, 0, 0), ((-1, -1, -1), (-1, 1, -1), (-1, 1, 1), (-1, -1, 1))),
         ((0, 0, 1), ((-1, -1, 1), (-1, 1, 1), (1, 1, 1), (1, -1, 1))),
         ((0, 0, -1), ((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1))))
SHADE = {(0, 1, 0): 0.0, (1, 0, 0): 0.42, (-1, 0, 0): 0.3, (0, 0, 1): 0.22, (0, 0, -1): 0.36}


def ortho_box(cv, x, z, w, d, h, color, cx, cy, yaw=ISO_YAW, elevation=ISO_ELEVATION, scale=1.0, outline=None):
    """Draw a box standing on the floor, centred on world (x, z), `w` wide,
    `d` deep and `h` tall, through the camera of `ortho_point`. Faces turned
    away are skipped; the rest are shaded per side (top lightest). Returns
    its depth, for sorting several boxes back to front."""
    hw, hd, hh = w / 2, d / 2, h / 2
    c, s = math.cos(yaw), math.sin(yaw)
    ce, se = math.cos(elevation), math.sin(elevation)
    line = dict(outline=outline, width=1.2) if outline else {}
    for n, corners in FACES:
        facing = (n[0] * s + n[2] * c) * ce + n[1] * se
        if facing <= 1e-3:
            continue
        pts = [ortho_point(x + sx * hw, hh + sy * hh, z + sz * hd, cx, cy, yaw, elevation, scale)[:2]
               for sx, sy, sz in corners]
        looks.fill(cv, pts, kit.mix(color, '#000000', SHADE[n]), **line)
    return ortho_point(x, hh, z, cx, cy, yaw, elevation, scale)[2]


GRID, TILE = 4, 64
HEIGHTS = ((32, 48, 22, 58),
           (42, 80, 36, 26),
           (22, 52, 70, 48),
           (54, 32, 42, 22))


def draw(n, cv):
    cx, cy = demo.W / 2, demo.H / 2 + 30
    yaw, el = to_isometric(demo.phase(n, 0.6, 2.3))
    half = GRID * TILE / 2 + 16
    # floor grid, then blocks back to front
    for i in range(GRID + 3):
        u = -half + i * (2 * half) / (GRID + 2)
        for a, b in (((u, -half), (u, half)), ((-half, u), (half, u))):
            looks.outline(cv, [ortho_point(a[0], 0, a[1], cx, cy, yaw, el)[:2],
                               ortho_point(b[0], 0, b[1], cx, cy, yaw, el)[:2]], demo.LINE, 2)
    boxes = []
    for r in range(GRID):
        for col in range(GRID):
            x, z = (col - (GRID - 1) / 2) * TILE, (r - (GRID - 1) / 2) * TILE
            depth = ortho_point(x, 0, z, cx, cy, yaw, el)[2]
            boxes.append((depth, x, z, HEIGHTS[r][col], demo.ACCENT if (r, col) == (1, 1) else demo.TEAL))
    for _, x, z, h, color in sorted(boxes):
        ortho_box(cv, x, z, TILE * 0.82, TILE * 0.82, h, color, cx, cy, yaw, el, outline=demo.BG)
    # a small axis gizmo: three axes closing to 120 degrees apart
    gx, gy = demo.W - 80, demo.H - 70
    for axis, color in (((36, 0, 0), demo.ACCENT), ((0, 36, 0), demo.INK), ((0, 0, 36), demo.TEAL)):
        ex, ey, _ = ortho_point(*axis, gx, gy, yaw, el)
        cv.line(gx, gy, ex, ey, color, width=3)
    p = demo.phase(n, 0.0, 0.3) * (1 - demo.phase(n, 0.6, 0.9))
    q = demo.phase(n, 2.2, 2.5)
    demo.word(cv, 'PLAN', 74, 40, size=18, color=demo.MUTED, font=demo.mono(18, 600), alpha=p)
    demo.word(cv, 'ISOMETRIC', 102, 40, size=18, color=demo.MUTED, font=demo.mono(18, 600), alpha=q)
    cv.mark('scene', cx - 200, cy - 190, 400, 330)


CAPABILITY = Capability(
    id='isometric-view',
    name='Isometric view',
    family='camera',
    group='3D motion',
    aliases=('isometric projection', 'iso view', 'isometric camera'),
    definition='The scene is seen without perspective from a corner angle where all three axes look '
               'equally shortened and 120 degrees apart, so parallel edges stay parallel.',
    phrasings=('show it from that classic flat 3D game angle with no vanishing point',
               'tip the camera into an isometric angle so the tiles become blocks',
               'draw the scene like an isometric illustration, corner-on from above'),
    related=('isometric-rotation', 'isometric-bar-rise', 'parallel-coordinates-draw', 'tilt',
             'perspective-crawl', 'pedestal'),
    api=('videobuilder.capabilities.camera.isometric_view.ortho_point',
         'videobuilder.capabilities.camera.isometric_view.to_isometric',
         'videobuilder.capabilities.camera.isometric_view.ortho_box',
         'videobuilder.capabilities.camera.isometric_view.ISO_ELEVATION'),
    demo=lambda: demo.film(draw),
)
