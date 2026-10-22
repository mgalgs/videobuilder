"""Virtual First-Down Line: a coloured stripe projected onto the field's
ground plane, so it stays pinned to one yard line while the camera moves and
players standing on it cover it, as if it were painted on the turf."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

FIELD_HALF = 26.65   # half the field's width, in yards
YELLOW = '#f5d23a'


def field_camera(x, height, z, yaw=0.0, pitch=0.35, focal=1500, cx=demo.W / 2, cy=demo.H / 2):
    """A pinhole camera over a flat field (yards; x across, y up, z downfield)
    standing at (x, height, z), turned `yaw` radians about the vertical and
    tilted `pitch` radians down. Returns `project(px, py, pz)` -> `(sx, sy,
    depth)` in frame px; depth <= 0 means behind the camera."""
    cy_, sy_ = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)

    def project(px, py, pz):
        dx, dy, dz = px - x, py - height, pz - z
        rx, rz = dx * cy_ - dz * sy_, dx * sy_ + dz * cy_
        up, depth = dy * cp + rz * sp, -dy * sp + rz * cp
        if depth <= 1e-6:
            return cx, cy, depth
        return cx + focal * rx / depth, cy - focal * up / depth, depth
    return project


def _clip_near(points, project, near=0.5):
    """Ground points (x, z) of a polygon, projected and clipped to depth > `near`."""
    proj = [project(x, 0.0, z) for x, z in points]
    out = []
    for i, (a, pa) in enumerate(zip(points, proj)):
        b, pb = points[(i + 1) % len(points)], proj[(i + 1) % len(proj)]
        if pa[2] > near:
            out.append(pa[:2])
        if (pa[2] > near) != (pb[2] > near):
            t = (near - pa[2]) / (pb[2] - pa[2])
            q = project(a[0] + (b[0] - a[0]) * t, 0.0, a[1] + (b[1] - a[1]) * t)
            out.append(q[:2])
    return out


def ground_polygon(cv, project, points, color, alpha=1.0):
    """Fill a polygon lying on the field, its corners given as ground (x, z)
    points, seen through `project` (from `field_camera`)."""
    pts = _clip_near(points, project)
    if len(pts) < 3:
        return
    c = cv.ctx
    c.new_path()
    c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    c.close_path()
    c.set_source_rgba(*vb.canvas.rgba(color, alpha))
    c.fill()


def first_down_line(cv, project, z, color=YELLOW, thickness=0.45, p=1.0, half=FIELD_HALF, alpha=0.92):
    """The first-down line at yard depth `z`, drawn on the turf through
    `project`: a band `thickness` yards deep running sideline to sideline,
    grown out from the left sideline as `p` goes 0 -> 1. Draw it after the
    field and before the players, so anyone standing on it covers it."""
    if p <= 0:
        return
    x1 = -half + 2 * half * vb.clamp01(p)
    t = thickness / 2
    ground_polygon(cv, project, [(-half, z - t), (x1, z - t), (x1, z + t), (-half, z + t)], color, alpha)


def _field(cv, project, z0, z1):
    for i, z in enumerate(range(int(z0) - int(z0) % 5, int(z1), 5)):  # mowing stripes
        ground_polygon(cv, project, [(-FIELD_HALF, z), (FIELD_HALF, z), (FIELD_HALF, z + 5), (-FIELD_HALF, z + 5)],
                       '#2f6b3e' if i % 2 else '#2a613a')
    for z in range(int(z0) - int(z0) % 5, int(z1) + 1, 5):  # yard lines
        ground_polygon(cv, project, [(-FIELD_HALF, z - 0.12), (FIELD_HALF, z - 0.12),
                                     (FIELD_HALF, z + 0.12), (-FIELD_HALF, z + 0.12)], demo.INK, 0.8)
        for x in (-7.0, 7.0):  # hash marks
            for k in range(1, 5):
                ground_polygon(cv, project, [(x - 0.5, z + k - 0.06), (x + 0.5, z + k - 0.06),
                                             (x + 0.5, z + k + 0.06), (x - 0.5, z + k + 0.06)], demo.INK, 0.6)
    for x in (-FIELD_HALF, FIELD_HALF):  # sidelines
        ground_polygon(cv, project, [(x - 0.3, z0), (x + 0.3, z0), (x + 0.3, z1), (x - 0.3, z1)], demo.INK, 0.9)


def _player(cv, project, x, z, color):
    fx, fy, d = project(x, 0.0, z)
    hx, hy, _ = project(x, 2.2, z)  # a figure a little over two yards tall
    if d <= 0.5:
        return
    h = fy - hy
    w = h * 0.34
    cv.sector(fx, fy, w * 0.75, 0, 2 * math.pi, (0, 0, 0, 0.35))  # contact shadow
    cv.rect(fx - w / 2, hy + h * 0.22, w, h * 0.78, color, radius=w * 0.3)
    demo.dot(cv, fx, hy + h * 0.12, r=h * 0.13, color=color)
    cv.rect(fx - w / 2, hy + h * 0.42, w, h * 0.08, demo.INK, alpha=0.7)  # jersey stripe


PLAYERS = [(-14, 39, demo.ACCENT), (-6, 42.9, demo.ACCENT), (-1, 40.5, demo.TEAL), (3, 43.1, demo.ACCENT),
           (9, 42.7, demo.TEAL), (15, 41, demo.ACCENT), (-10, 46, demo.TEAL), (6, 47.5, demo.TEAL),
           (19, 43.0, demo.TEAL), (-19, 44, demo.ACCENT), (0, 50, demo.TEAL), (-3, 36, demo.ACCENT)]
LINE_Z = 43.0


def draw(n, cv):
    t = n / (demo.FPS * demo.SECONDS)
    s = t * t * (3 - 2 * t)  # smoothstep: the camera eases in and out of its move
    cam_z = -2 + 8 * s
    project = field_camera(x=-10 + 20 * s, height=30 - 6 * s, z=cam_z, yaw=0.16 - 0.32 * s, pitch=0.5 - 0.06 * s,
                           focal=1000)
    cv.fill('#0e1a14')
    _field(cv, project, cam_z, 100)
    first_down_line(cv, project, LINE_Z, thickness=0.6, p=vb.ease_out_quint(demo.phase(n, 0.3, 1.0)))
    for x, z, color in sorted(PLAYERS, key=lambda q: -project(q[0], 0.0, q[1])[2]):  # far to near
        _player(cv, project, x, z, color)
    f = demo.font(30, 800)
    cv.rect(48, 44, 220, 62, demo.BG, radius=10, alpha=0.85)
    vb.text.draw(cv, ['1ST & 10'], f, 72, 56, YELLOW)
    a, b, _ = project(-FIELD_HALF, 0.0, LINE_Z)
    c, d, _ = project(FIELD_HALF, 0.0, LINE_Z)
    cv.mark('line', min(a, c), min(b, d) - 6, abs(c - a), abs(d - b) + 12)


CAPABILITY = Capability(
    id='virtual-first-down-line',
    name='Virtual first-down line',
    family='broadcast',
    group='Sports graphics',
    aliases=('yellow line overlay', 'field line graphic', 'first-down marker line'),
    definition='A bright line drawn across a sports field in true perspective that holds its yard line as the '
               'camera moves, with players standing in front of it as if it were painted on the grass.',
    phrasings=('put the yellow first-down line on the field and keep it stuck there as the camera pans',
               'a line painted onto the turf in perspective that players walk over',
               'show the line to gain across the field like on a football broadcast'),
    related=('line-chart-draw-on', 'callout-line-with-label', 'crt-scanlines', 'streamlines',
             'isolines-contour-animation', 'speed-lines'),
    api=('videobuilder.capabilities.broadcast.virtual_first_down_line.first_down_line',
         'videobuilder.capabilities.broadcast.virtual_first_down_line.field_camera',
         'videobuilder.capabilities.broadcast.virtual_first_down_line.ground_polygon'),
    demo=lambda: demo.film(draw),
)
