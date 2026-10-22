"""Low-poly faceting: a 3D form built from a handful of big triangles, each
filled with one flat shade by how squarely it faces the light, so as the form
turns the facets flick between tones instead of shading smoothly."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ..schema import Technique


def _unit(v):
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / n for c in v)


def _cross(u, v):
    return (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(u, v):
    return u[0] * v[0] + u[1] * v[1] + u[2] * v[2]


def low_poly_mesh(subdivide=0, jitter=0.0, seed=0):
    """A closed low-poly ball of radius about 1: an icosahedron (20 faces),
    each triangle split into four `subdivide` times (80, 320 ...), with every
    vertex pushed in or out by up to `jitter` of the radius so the facets come
    out uneven, like a rock or gem. Returns `(verts, faces)`: `verts` a list of
    (x, y, z), `faces` index triples wound so their normals point outwards."""
    g = (1 + math.sqrt(5)) / 2
    verts = [_unit(v) for v in ((-1, g, 0), (1, g, 0), (-1, -g, 0), (1, -g, 0), (0, -1, g), (0, 1, g),
                                (0, -1, -g), (0, 1, -g), (g, 0, -1), (g, 0, 1), (-g, 0, -1), (-g, 0, 1))]
    faces = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2),
             (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5),
             (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    for _ in range(subdivide):
        mids, out = {}, []

        def mid(a, b):
            k = (min(a, b), max(a, b))
            if k not in mids:
                mids[k] = len(verts)
                verts.append(_unit(tuple((p + q) / 2 for p, q in zip(verts[a], verts[b]))))
            return mids[k]
        for a, b, c in faces:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            out += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        faces = out
    rnd = random.Random(seed)
    verts = [tuple(c * (1 + rnd.uniform(-jitter, jitter)) for c in v) for v in verts]
    fixed = []
    for a, b, c in faces:  # wind every face outwards, whatever the jitter did
        n = _cross(_sub(verts[b], verts[a]), _sub(verts[c], verts[a]))
        centre = tuple((p + q + r) / 3 for p, q, r in zip(verts[a], verts[b], verts[c]))
        fixed.append((a, b, c) if _dot(n, centre) > 0 else (a, c, b))
    return verts, fixed


def draw_faceted(cv, verts, faces, cx, cy, size, yaw=0.0, pitch=0.0, roll=0.0, color=demo.ACCENT,
                 shadow='#000000', light=(-0.75, -0.55, 0.38), ambient=0.22, focal=4.0, edge=None,
                 edge_width=1.0):
    """Draw the mesh `verts, faces` (see `low_poly_mesh`) centred at (cx, cy),
    `size` px per unit, turned by `roll` (about the view axis), `pitch` (about
    the horizontal) and `yaw` (about the vertical), radians. Every visible
    facet gets one flat tone between `shadow` and `color` by how squarely it
    faces `light` (x right, y down, z towards the viewer), floored at
    `ambient`. `focal` is the camera distance in mesh units (smaller is more
    perspective). `edge` strokes the facet sides. Returns the frame box."""
    cy_, sy_ = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cr, sr = math.cos(roll), math.sin(roll)
    world = []
    for x, y, z in verts:
        x, y = x * cr - y * sr, x * sr + y * cr
        y, z = y * cp - z * sp, y * sp + z * cp
        x, z = x * cy_ + z * sy_, -x * sy_ + z * cy_
        world.append((x, y, z))
    eye = (0.0, 0.0, focal)
    flat = []
    for x, y, z in world:
        k = focal / max(focal - z, 1e-3)
        flat.append((cx + x * size * k, cy + y * size * k))
    lit = _unit(light)
    drawn = []
    for a, b, c in faces:
        pa, pb, pc = world[a], world[b], world[c]
        n = _unit(_cross(_sub(pb, pa), _sub(pc, pa)))
        centre = tuple((p + q + r) / 3 for p, q, r in zip(pa, pb, pc))
        if _dot(n, _sub(eye, centre)) <= 0:
            continue  # faces away from the camera
        k = ambient + (1 - ambient) * max(0.0, _dot(n, lit))
        drawn.append((centre[2], (a, b, c), kit.mix(shadow, color, k)))
    drawn.sort(key=lambda d: d[0])  # back to front
    ctx = cv.ctx
    for _, (a, b, c), tone in drawn:
        ctx.new_path()
        ctx.move_to(*flat[a])
        ctx.line_to(*flat[b])
        ctx.line_to(*flat[c])
        ctx.close_path()
        ctx.set_source_rgba(*vb.rgba(tone))
        ctx.fill_preserve()
        ctx.set_line_width(1.0)  # a hairline in the facet's own tone hides the anti-aliasing seams
        ctx.stroke()
        if edge:
            ctx.move_to(*flat[a])
            ctx.line_to(*flat[b])
            ctx.line_to(*flat[c])
            ctx.close_path()
            ctx.set_source_rgba(*vb.rgba(edge, 0.35))
            ctx.set_line_width(edge_width)
            ctx.stroke()
    xs, ys = [p[0] for p in flat], [p[1] for p in flat]
    box = (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
    cv.mark('facets', *box)
    return box


MESH = low_poly_mesh(subdivide=1, jitter=0.1, seed=4)


def draw(n, cv):
    t = n / demo.FPS
    cx, cy, size = demo.W / 2, demo.H / 2 - 30, 200
    ground = cy + size + 70
    ctx = cv.ctx  # a soft contact shadow on the floor
    ctx.save()
    ctx.translate(cx, ground)
    ctx.scale(1, 0.14)
    ctx.new_path()
    ctx.arc(0, 0, size * 0.9, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgba(0, 0, 0, 0.35)
    ctx.fill()
    draw_faceted(cv, *MESH, cx, cy, size, yaw=0.5 + 0.75 * t, pitch=0.35 + 0.18 * math.sin(t * 1.3),
                 roll=0.2, color=demo.ACCENT, shadow=demo.BG)


TECHNIQUE = Technique(
    id='low-poly-faceting',
    name='Low-poly faceting',
    family='camera',
    group='3D motion',
    aliases=('flat-shaded low poly', 'faceted geometry', 'low poly', 'flat shading'),
    definition='A 3D shape is made of a few large triangles, each painted one solid shade by how it faces '
               'the light, so it turns like a cut gem with crisp facets instead of smooth shading.',
    phrasings=('a spinning low-poly rock with flat shaded triangles',
               'make the 3D object look faceted, like a cut gemstone',
               'chunky triangle geometry where every face is one flat colour'),
    related=('gooch-shading', 'cel-shading-look', 'fresnel-edge-glow', 'cross-hatch-shading',
             'matcap-shading', 'angled-lower-third'),
    api=('videobuilder.techniques.camera.low_poly_faceting.draw_faceted',
         'videobuilder.techniques.camera.low_poly_faceting.low_poly_mesh'),
    demo=lambda: demo.film(draw),
)
