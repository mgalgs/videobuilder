"""Wireframe Reveal: a 3D model first appears as bare edges, traced on line
by line, then a fill line climbs it from the bottom and leaves solid, shaded
faces behind, so the outline drawing becomes a finished object."""
import math

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Technique


def icosahedron(r=1.0):
    """A 20-faced solid of radius `r` as (vertices, faces): vertices are
    (x, y, z) tuples, faces are vertex-index triples wound outward."""
    t = (1 + math.sqrt(5)) / 2
    k = r / math.sqrt(1 + t * t)
    verts = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
             (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    faces = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2),
             (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5),
             (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    return [(x * k, y * k, z * k) for x, y, z in verts], faces


def _edges(faces):
    seen = []
    for f in faces:
        for i in range(len(f)):
            e = tuple(sorted((f[i], f[(i + 1) % len(f)])))
            if e not in seen:
                seen.append(e)
    return seen


def _shade(color, k):
    r, g, b, a = rgba(color)
    return (r * k, g * k, b * k, a)


def wireframe_reveal(cv, verts, faces, cx, cy, size, trace, fill, yaw=0.0, pitch=0.3, color=demo.TEAL,
                     line_color=None, line_width=3, distance=4.0, light=(-0.4, -0.7, -0.6), stagger=0.6):
    """Draw a mesh (`verts`, `faces` as from `icosahedron`) centred at (cx, cy),
    `size` px per model unit, turned `yaw` then `pitch` radians, in perspective
    (`distance` model units from the camera).

    `trace` (0 -> 1) draws the wireframe on: every edge, front and back,
    grows from one end, the edges starting one after another over the first
    `stagger` of the run. `fill` (0 -> 1) then raises a level from the
    model's bottom to its top: below it the faces are solid, culled and lit
    from `light`; above it the wireframe still shows. Returns the model's
    on-screen Box."""
    cy_, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cam = []
    for x, y, z in verts:
        x, z = x * cy_ + z * sy, -x * sy + z * cy_
        y, z = y * cp - z * sp, y * sp + z * cp
        cam.append((x, y, z))
    scr = [(cx + x * size * distance / (distance + z), cy - y * size * distance / (distance + z)) for x, y, z in cam]
    xs, ys = [p[0] for p in scr], [p[1] for p in scr]
    box = vb.Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
    level = box.y + box.h * (1 - vb.clamp01(fill)) - 1  # screen y of the fill line
    ctx = cv.ctx
    line = line_color or color

    if fill > 0:
        lx, ly, lz = light
        ln = math.sqrt(lx * lx + ly * ly + lz * lz)
        solid = []
        for f in faces:
            a, b, c = (cam[i] for i in f)
            ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
            vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
            nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
            nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            centre = [(a[j] + b[j] + c[j]) / 3 for j in range(3)]
            if nx * centre[0] + ny * centre[1] + nz * (centre[2] + distance) >= 0:
                continue  # faces away from the camera
            lit = max(0.0, (nx * lx - ny * ly + nz * lz) / (nl * ln))  # light points toward the lamp, y down
            solid.append((centre[2], f, 0.45 + 0.55 * lit))
        with cv.clip(box.x - 10, level, box.w + 20, box.y + box.h - level + 10):
            for _, f, k in sorted(solid, key=lambda s: -s[0]):
                ctx.new_path()
                ctx.move_to(*scr[f[0]])
                for i in f[1:]:
                    ctx.line_to(*scr[i])
                ctx.close_path()
                ctx.set_source_rgba(*_shade(color, k))
                ctx.fill_preserve()
                ctx.set_line_width(1)
                ctx.stroke()  # seal hairline gaps between faces
        if fill < 1:
            cv.line(box.x - 6, level, box.x + box.w + 6, level, line, width=line_width)

    if fill < 1:
        edges = _edges(faces)
        n = len(edges)
        span = 1 - stagger
        with cv.clip(box.x - 10, box.y - 10, box.w + 20, level - box.y + 10):
            ctx.set_line_width(line_width)
            ctx.set_line_cap(1)  # round
            ctx.set_source_rgba(*rgba(line))
            for i, (a, b) in enumerate(edges):
                q = vb.clamp01((trace - stagger * i / max(1, n - 1)) / span) if span > 0 else float(trace >= 1)
                if q <= 0:
                    continue
                (x0, y0), (x1, y1) = scr[a], scr[b]
                ctx.move_to(x0, y0)
                ctx.line_to(x0 + (x1 - x0) * q, y0 + (y1 - y0) * q)
            ctx.stroke()
    return box


MESH = icosahedron()


def draw(n, cv):
    t = n / demo.FPS
    trace = vb.ease_in_out_quart(demo.phase(n, 0.1, 1.3))
    fill = vb.ease_in_out_quart(demo.phase(n, 1.4, 2.6))
    box = wireframe_reveal(cv, *MESH, demo.W / 2, demo.H / 2, demo.H * 0.34, trace, fill,
                           yaw=0.35 + 0.35 * t, pitch=0.35)
    cv.mark('model', *box)


TECHNIQUE = Technique(
    id='wireframe-reveal',
    name='Wireframe reveal',
    family='camera',
    group='3D motion',
    aliases=('wireframe build', 'mesh outline reveal', 'wireframe to solid'),
    definition='A 3D object shows up first as a see-through skeleton of lines, '
               'then solid shaded surfaces fill in over that skeleton until the object looks finished.',
    phrasings=('draw the 3D model as lines first, then fill it in solid',
               'show the mesh outline and let the surfaces build up over it',
               'start with a wireframe and turn it into the real object'),
    related=('line-draw-logo-reveal', 'logo-build-on-reveal', 'zoom-out-reveal', 'text-reveal-through-shape-mask',
             'curtain-reveal', 'device-mockup-slide-in'),
    api=('videobuilder.techniques.camera.wireframe_reveal.wireframe_reveal',
         'videobuilder.techniques.camera.wireframe_reveal.icosahedron'),
    demo=lambda: demo.film(draw),
)
