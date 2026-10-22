"""Ink outline: a flat-shaded solid turning in light, with a heavy dark line
round its silhouette and finer lines along its creases, like a toon render
or a comic panel inked over a 3D model."""
import itertools
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ..schema import Capability

INK = '#0d0f14'


def _sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _unit(v):
    n = math.sqrt(_dot(v, v)) or 1.0
    return tuple(c / n for c in v)


def _normal(pts, face):
    """The outward unit normal of a convex `face` (indices into `pts`) of a
    solid centred on the origin, by Newell's method."""
    n = [0.0, 0.0, 0.0]
    for i, j in zip(face, face[1:] + face[:1]):
        a, b = pts[i], pts[j]
        n[0] += (a[1] - b[1]) * (a[2] + b[2])
        n[1] += (a[2] - b[2]) * (a[0] + b[0])
        n[2] += (a[0] - b[0]) * (a[1] + b[1])
    return _unit(n)


def solid(verts, normals, tol=1e-6):
    """The faces of the convex solid with corners `verts` and face directions
    `normals`: for each normal, the corners furthest along it, in order round
    the face. Returns `faces` (tuples of indices into `verts`) for `ink_outline`."""
    faces = []
    for n in normals:
        n = _unit(n)
        top = max(_dot(v, n) for v in verts)
        idx = [i for i, v in enumerate(verts) if _dot(v, n) > top - tol]
        c = tuple(sum(verts[i][k] for i in idx) / len(idx) for k in range(3))
        u = _unit(_sub(verts[idx[0]], c))
        w = _cross(n, u)
        idx.sort(key=lambda i: math.atan2(_dot(_sub(verts[i], c), w), _dot(_sub(verts[i], c), u)))
        faces.append(tuple(idx))
    return tuple(faces)


def turn(v, yaw, pitch, roll=0.0):
    """`v` rotated by `yaw` about the vertical axis, then `pitch` about the
    horizontal one, then `roll` about the view axis (radians). Axes: x right,
    y down, z towards the viewer."""
    x, y, z = v
    c, s = math.cos(yaw), math.sin(yaw)
    x, z = c * x + s * z, -s * x + c * z
    c, s = math.cos(pitch), math.sin(pitch)
    y, z = c * y - s * z, s * y + c * z
    c, s = math.cos(roll), math.sin(roll)
    return c * x - s * y, s * x + c * y, z


def ink_outline(cv, verts, faces, cx, cy, size, yaw=0.0, pitch=0.0, roll=0.0, colors=(demo.INK,),
                light=(-0.5, -0.7, 0.6), ink=INK, width=9.0, crease=3.0, crease_angle=15.0, amount=1.0):
    """Draw the solid `verts`/`faces` (see `solid`; faces wound either way)
    turned by `yaw`/`pitch`/`roll`, centred at (cx, cy) with 1 unit = `size`
    px, flat-shaded towards `light`, then inked: a `width` px line where
    the visible surface meets the background (the silhouette) and a `crease`
    px line on every visible edge whose faces bend more than `crease_angle`
    degrees. `colors[i % len(colors)]` is face i's base colour. `amount`
    (0..1) scales both line weights, to ink the outline on or off."""
    pts = [turn(v, yaw, pitch, roll) for v in verts]
    centre = tuple(sum(p[k] for p in pts) / len(pts) for k in range(3))
    light = _unit(light)
    normals = []
    for f in faces:
        n = _normal(pts, list(f))
        fc = tuple(sum(pts[i][k] for i in f) / len(f) for k in range(3))
        normals.append(n if _dot(n, _sub(fc, centre)) >= 0 else tuple(-c for c in n))
    front = [n[2] > 1e-6 for n in normals]
    xy = [(cx + p[0] * size, cy + p[1] * size) for p in pts]
    ctx = cv.ctx
    order = sorted(range(len(faces)), key=lambda i: sum(pts[j][2] for j in faces[i]) / len(faces[i]))
    for i in order:
        if not front[i]:
            continue
        lit = 0.42 + 0.58 * max(0.0, _dot(normals[i], light))
        base = colors[i % len(colors)]
        tone = kit.mix('#000000', base, lit) if lit < 1 else base
        ctx.new_path()
        for j in faces[i]:
            ctx.line_to(*xy[j])
        ctx.close_path()
        ctx.set_source_rgba(*vb.rgba(tone))
        ctx.fill_preserve()
        ctx.set_line_width(1.0)          # hairline in the face colour closes antialiasing seams
        ctx.stroke()
    if amount <= 0:
        return
    edges = {}
    for i, f in enumerate(faces):
        for a, b in zip(f, f[1:] + f[:1]):
            edges.setdefault((min(a, b), max(a, b)), []).append(i)
    cos_crease = math.cos(math.radians(crease_angle))
    silhouette, creases = [], []
    for (a, b), fs in edges.items():
        seen = [front[i] for i in fs]
        if any(seen) and not all(seen) or len(fs) == 1 and seen[0]:
            silhouette.append((a, b))
        elif all(seen) and _dot(normals[fs[0]], normals[fs[1]]) < cos_crease:
            creases.append((a, b))
    ctx.set_source_rgba(*vb.rgba(ink))
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    for lines, w in ((creases, crease), (silhouette, width)):
        if w * amount <= 0:
            continue
        ctx.new_path()
        for a, b in lines:
            ctx.move_to(*xy[a])
            ctx.line_to(*xy[b])
        ctx.set_line_width(w * amount)
        ctx.stroke()
    xs, ys = [p[0] for p in xy], [p[1] for p in xy]
    cv.mark('ink-outline', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


# A truncated octahedron: corners at every arrangement of (0, +-1, +-2);
# eight hexagons and six squares.
_VERTS = tuple(sorted({p for a in (1, -1) for b in (2, -2) for p in itertools.permutations((0, a, b))}))
_NORMALS = tuple((sx, sy, sz) for sx in (1, -1) for sy in (1, -1) for sz in (1, -1)) + \
    ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
_FACES = solid(_VERTS, _NORMALS)
_COLORS = ('#dfe3ef',) * 8 + ('#f2b632',) * 6   # pale hexagons, golden squares


def _backdrop(cv, cx, cy, r):
    grad = cairo.RadialGradient(cx, cy, 0, cx, cy, r)
    grad.add_color_stop_rgba(0, *vb.rgba('#6c7488', 1.0))
    grad.add_color_stop_rgba(1, *vb.rgba(demo.BG, 1.0))
    cv.ctx.rectangle(0, 0, demo.W, demo.H)
    cv.ctx.set_source(grad)
    cv.ctx.fill()


def draw(n, cv):
    t = n / demo.FPS
    cx, cy = demo.W / 2, demo.H / 2 - 16
    _backdrop(cv, cx, cy, 330)
    floor = cy + 210                     # a soft ground shadow under the floating solid
    ctx = cv.ctx
    ctx.save()
    ctx.translate(cx, floor)
    ctx.scale(1, 0.12)
    ctx.new_path()
    ctx.arc(0, 0, 140, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgba(*vb.rgba('#000000', 0.35))
    ctx.fill()
    ink = vb.ease_out_quint(demo.phase(n, 0.5, 1.3))   # plain at first, then the ink goes on
    ink_outline(cv, _VERTS, _FACES, cx, cy + 6 * math.sin(2 * t), 80,
                yaw=0.5 + 0.9 * t, pitch=0.55 + 0.12 * math.sin(1.4 * t), roll=0.15,
                colors=_COLORS, width=7, crease=2.5, amount=ink)


CAPABILITY = Capability(
    id='ink-outline',
    name='Ink outline',
    family='camera',
    group='Shader looks',
    aliases=('inverted hull outline', 'silhouette outline', 'toon outline', 'Sobel outline',
             'edge line art', 'cartoon outline'),
    definition='A 3D object is drawn with a bold dark line tracing its outer edge and thinner lines '
               'along its sharp folds, so it reads like an inked cartoon as it turns.',
    phrasings=('give the 3D shape a thick black cartoon outline',
               'make the model look hand-inked, with lines on its edges',
               'toon-style render with dark lines round the silhouette and the corners'),
    related=('stroke-draw-on', 'line-draw-logo-reveal', 'outline-to-fill', 'ink-bleed',
             'ink-splash-spread', 'ink-spread-reveal'),
    api=('videobuilder.capabilities.camera.ink_outline.ink_outline',
         'videobuilder.capabilities.camera.ink_outline.solid',
         'videobuilder.capabilities.camera.ink_outline.turn'),
    demo=lambda: demo.film(draw),
)
