"""Bend deformer: a flat 3D sheet is curved about an axis across it, every
point wrapped onto an arc of the same length, so the sheet flexes from flat
into a curl (and at a full turn, a tube) seen in perspective."""
import math

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Capability


def bend(points, angle, length):
    """3D `points` (x, y, z) bent by `angle` degrees about an axis parallel to
    y through the origin. The stretch x in [-length/2, length/2] is wrapped
    onto an arc of that same length turning through `angle` in total, curling
    towards +z (negative `angle` curls towards -z); points beyond the stretch
    carry on along the end tangents, as a deformer's clamped ends do. 0 is
    flat; 360 rolls the stretch into a closed tube. `z` is the offset off the
    surface, kept along the bent normal, so thickness survives the bend."""
    theta = math.radians(angle)
    if abs(theta) < 1e-6:
        return [tuple(p) for p in points]
    r = length / theta
    half = length / 2
    out = []
    for x, y, z in points:
        u = max(-half, min(half, x))
        phi = u / r
        s, c = math.sin(phi), math.cos(phi)
        rr = r - z  # z is measured off the surface, towards the centre of the bend when > 0
        bx, bz = rr * s, r - rr * c
        extra = x - u  # past a clamped end: straight on along the tangent there
        out.append((bx + extra * c, y, bz + extra * s))
    return out


def _shade(color, k):
    r, g, b, a = rgba(color)
    return (round(r * 255 * k), round(g * 255 * k), round(b * 255 * k), a)


def draw_bent_sheet(cv, cx, cy, w, h, angle, color, back_color=None, grid=None, yaw=24.0, pitch=-16.0,
                    distance=1800, cols=48, rows=6, alpha=1.0):
    """Draw a `w` x `h` px sheet centred at (cx, cy), bent by `angle` degrees
    (see `bend`) about its vertical centre line, in perspective. The camera
    looks at it turned `yaw` degrees about the vertical and `pitch` about the
    horizontal, so the curl reads in depth; `distance` is the camera distance.
    The sheet is cut into `cols` x `rows` facets, lit by their facing, front in
    `color` and back in `back_color` (default: `color` darkened); `grid`
    draws the facet lines in that colour, the deformer's mesh. Returns the
    Box of the drawn sheet."""
    ya, pa = math.radians(yaw), math.radians(pitch)
    cyw, syw, cp, sp = math.cos(ya), math.sin(ya), math.cos(pa), math.sin(pa)

    def view(p):
        x, y, z = p
        x, z = x * cyw + z * syw, -x * syw + z * cyw
        y, z = y * cp - z * sp, y * sp + z * cp
        return x, y, z

    def project(p):
        x, y, z = p
        f = distance / (distance + z)
        return cx + x * f, cy + y * f

    xs = [-w / 2 + w * i / cols for i in range(cols + 1)]
    ys = [-h / 2 + h * j / rows for j in range(rows + 1)]
    pts = bend([(x, y, 0.0) for y in ys for x in xs], angle, w)
    cam = [view(p) for p in pts]
    scr = [project(p) for p in cam]
    at = lambda i, j: j * (cols + 1) + i  # noqa: E731

    faces = []
    for j in range(rows):
        for i in range(cols):
            idx = (at(i, j), at(i + 1, j), at(i + 1, j + 1), at(i, j + 1))
            a, b, d = cam[idx[0]], cam[idx[1]], cam[idx[3]]
            ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
            vx, vy, vz = d[0] - a[0], d[1] - a[1], d[2] - a[2]
            nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
            ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            facing = nz / ln  # > 0: the front of the sheet faces the camera
            depth = sum(cam[k][2] for k in idx) / 4
            faces.append((depth, idx, facing, ny / ln))

    ctx = cv.ctx
    back = back_color or _shade(color, 0.55)
    with cv.layer(opacity=alpha):
        for depth, idx, facing, ny in sorted(faces, key=lambda f: -f[0]):
            poly = [scr[k] for k in idx]
            ctx.new_path()
            ctx.move_to(*poly[0])
            for x, y in poly[1:]:
                ctx.line_to(x, y)
            ctx.close_path()
            k = 0.45 + 0.55 * abs(facing) - 0.1 * ny * (1 if facing >= 0 else -1)
            ctx.set_source_rgba(*rgba(_shade(color if facing >= 0 else back, max(0.25, min(1.0, k)))))
            if grid:
                ctx.fill_preserve()
                ctx.set_source_rgba(*rgba(grid))
                ctx.set_line_width(1.2)
                ctx.stroke()
            else:
                ctx.fill()
    sx = [p[0] for p in scr]
    sy = [p[1] for p in scr]
    return vb.Box(min(sx), min(sy), max(sx) - min(sx), max(sy) - min(sy))


# (time s, bend degrees): flat, curl away, roll almost shut, flex the other way, flat again
KEYS = ((0.2, 0), (0.9, 150), (1.5, 320), (2.2, -140), (2.8, 0))


def bend_at(t, keys=KEYS):
    """The bend angle at `t` seconds, eased between `keys`."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, a0), (t1, a1) in zip(keys, keys[1:]):
        if t <= t1:
            return a0 + (a1 - a0) * vb.ease_in_out_quart((t - t0) / (t1 - t0))
    return keys[-1][1]


def draw(n, cv):
    angle = bend_at(n / demo.FPS)
    box = draw_bent_sheet(cv, demo.W / 2, demo.H / 2 - 50, 780, 300, angle, demo.ACCENT, back_color=demo.TEAL,
                          grid=(0, 0, 0, 0.28))
    cv.mark('sheet', *box)
    demo.word(cv, f'bend {round(angle):+d}°', demo.W / 2, demo.H - 70, size=34, color=demo.MUTED,
              weight=600, font=demo.mono(34, 600))


CAPABILITY = Capability(
    id='bend-deformer',
    name='Bend deformer',
    family='camera',
    group='3D motion',
    aliases=('bend modifier', 'curl deformer', 'bend deform'),
    definition='A flat plane in 3D is wrapped onto an arc about an axis across it, '
               'curving smoothly from flat into a curl or tube while keeping its length.',
    phrasings=('curl the card up in 3D like a sheet of paper rolling',
               'bend the flat panel into an arc and then back',
               'wrap the plane around into a cylinder'),
    related=('arc-bend-morph', 'arcs', 'line-to-polygon-transform', 'flight-arc', 'bezier-handle-bend',
             'refraction-ripple'),
    api=('videobuilder.capabilities.camera.bend_deformer.draw_bent_sheet',
         'videobuilder.capabilities.camera.bend_deformer.bend'),
    demo=lambda: demo.film(draw),
)
