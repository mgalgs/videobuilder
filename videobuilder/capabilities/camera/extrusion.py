"""Extrusion: a flat shape is pushed back into space, its outline sweeping
out solid side walls behind it, and how deep it goes is what animates -- a
paper-thin shape grows into a slab."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ...canvas import rgba
from ...looks import kit as looks

FOCAL = 1100.0
LIGHT = (-0.45, -0.75, -0.5)  # towards the light: up, left and in front


def polygon(cx, cy, r, sides, turn=0.0):
    """A regular polygon of `sides` corners, radius `r`, as a point list
    about (cx, cy); `turn` rotates it (degrees). Feed it to `draw_extrusion`
    with cx = cy = 0 so it extrudes about its own centre."""
    a0 = math.radians(turn) - math.pi / 2
    return [(cx + r * math.cos(a0 + 2 * math.pi * i / sides), cy + r * math.sin(a0 + 2 * math.pi * i / sides))
            for i in range(sides)]


def project(x, y, z, cx, cy, yaw, pitch, focal=FOCAL):
    """Point (x, y, z) of the shape's own space (+z goes back, away from the
    face) turned by `yaw` then `pitch` degrees and seen through a lens of
    `focal` px centred on (cx, cy) -> (screen x, screen y, view depth)."""
    cyw, syw = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    x1, z1 = x * cyw + z * syw, -x * syw + z * cyw
    y2, z2 = y * cp - z1 * sp, y * sp + z1 * cp
    d = focal / max(80.0, focal + z2)
    return cx + x1 * d, cy + y2 * d, z2


def _shade(color, k):
    r, g, b, _ = rgba(color)
    return tuple(round(255 * min(1.0, c * k)) for c in (r, g, b))


def draw_extrusion(cv, points, depth, cx, cy, face, side=None, yaw=28.0, pitch=16.0, focal=FOCAL,
                   edge=None, edge_width=2.0):
    """Draw the closed polygon `points` (px about its own origin) extruded
    `depth` px back into space, centred at (cx, cy) and turned by `yaw` and
    `pitch` degrees under one perspective lens: the front face in `face`, the
    side walls in `side` (default: `face` darkened), each wall lit by how
    squarely it meets a light from the upper left, back walls culled and the
    rest painted far to near. Animate `depth` from 0 up to make a flat shape
    gain thickness; keep the angles fixed or drift them slowly so the depth
    reads. Works for any simple polygon. Returns the Box of the screen outline."""
    pts = [tuple(p) for p in points]
    if sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1])) < 0:
        pts = pts[::-1]  # one winding (clockwise on screen) so wall normals point outwards
    side = side or _shade(face, 0.6)
    P = lambda x, y, z: project(x, y, z, cx, cy, yaw, pitch, focal)  # noqa: E731
    front = [P(x, y, 0) for x, y in pts]
    back = [P(x, y, depth) for x, y in pts]
    ln = math.sqrt(sum(c * c for c in LIGHT))
    light = [c / ln for c in LIGHT]
    cyw, syw = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    walls = []
    if depth > 0.5:
        n = len(pts)
        for i in range(n):
            j = (i + 1) % n
            quad = [front[i], front[j], back[j], back[i]]
            # Cull walls facing away: on screen their corners wind the other way.
            area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(quad, quad[1:] + quad[:1]))
            if area >= 0:
                continue
            (x0, y0), (x1, y1) = pts[i], pts[j]
            nx, ny = y1 - y0, -(x1 - x0)  # outward normal in the shape's plane
            nl = math.hypot(nx, ny) or 1.0
            nx, ny = nx / nl, ny / nl
            vx, vz = nx * cyw, -nx * syw  # the normal through the same turn as the points
            vy, vz = ny * cp - vz * sp, ny * sp + vz * cp
            lit = max(0.0, vx * light[0] + vy * light[1] + vz * light[2])
            walls.append((sum(q[2] for q in quad) / 4, quad, 0.55 + 0.6 * lit))
    for _, quad, k in sorted(walls, key=lambda w: -w[0]):
        looks.fill(cv, [q[:2] for q in quad], _shade(side, k), outline=_shade(side, k * 0.95), width=1)
    looks.fill(cv, [q[:2] for q in front], face, outline=edge, width=edge_width if edge else 0)
    xs = [q[0] for q in front + back]
    ys = [q[1] for q in front + back]
    return vb.Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def draw(n, cv):
    grow = vb.ease_in_out_quart(demo.phase(n, 0.4, 2.3))
    depth = 300 * grow
    yaw = 8 + 26 * vb.ease_in_out_quart(demo.phase(n, 0.0, 3.0))
    pitch = 8 + 10 * vb.ease_in_out_quart(demo.phase(n, 0.0, 3.0))
    cx, cy = demo.W / 2 - 40, demo.H / 2 - 20
    cv.shape_shadow([(cx - 200, cy + 230), (cx + 260, cy + 230), (cx + 300, cy + 270), (cx - 160, cy + 270)],
                    blur=30, color=(0, 0, 0, 0.45))
    box = draw_extrusion(cv, polygon(0, 0, 190, 6, turn=30), depth, cx, cy, demo.ACCENT, demo.TEAL, yaw, pitch)
    cv.mark('extrusion', *box)


CAPABILITY = Capability(
    id='extrusion',
    name='Extrusion',
    family='camera',
    group='3D motion',
    aliases=('extruded depth', 'depth extrude', 'extrude'),
    definition='A flat outline is pushed back into space so solid side walls sweep out behind it, '
               'and the thickness keeps growing until the shape reads as a solid slab.',
    phrasings=('make the flat logo shape grow thickness so it turns into a 3D block',
               'push the hexagon back into depth so you can see its sides',
               'give the 2D shape an extruded side that gets deeper over time'),
    related=('extrusion-depth-reveal', 'solid-drawing', 'volume-preservation', 'shape-morph',
             'isometric-bar-rise', 'polygon-subdivision'),
    api=('videobuilder.capabilities.camera.extrusion.draw_extrusion',
         'videobuilder.capabilities.camera.extrusion.project',
         'videobuilder.capabilities.camera.extrusion.polygon'),
    demo=lambda: demo.film(draw),
)
