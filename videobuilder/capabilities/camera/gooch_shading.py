"""Gooch Shading: a 3D form lit from warm to cool instead of light to dark --
the side facing the light goes yellow-orange, the side turned away goes
blue -- with a dark ink outline round its silhouette, the technical
illustration look."""
import math
from functools import lru_cache

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

WARM = '#ffc21a'    # what a surface facing the light tends to
COOL = '#3d4fd6'    # what a surface turned away tends to
LIGHT = (-0.7, -0.55, 0.4)   # towards the light: up-left, a little in front


def _unit(v):
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / n for c in v)


def gooch_tone(normal, light=LIGHT, warm=WARM, cool=COOL, base=None, tint=0.25, highlight=0.6, shine=40):
    """The Gooch colour (r, g, b, 0-255) of a surface with unit `normal`:
    blended from `cool` (turned fully away from `light`) to `warm` (facing
    it), never darkening to black. `base`, if given, is mixed into both
    ends by `tint` so the object keeps a hint of its own colour. A white
    highlight of strength `highlight` and tightness `shine` sits where the
    light glints towards the viewer. Axes: x right, y down, z towards the viewer."""
    lx, ly, lz = _unit(light)
    nx, ny, nz = normal
    t = (1 + nx * lx + ny * ly + nz * lz) / 2
    w, c = vb.rgba(warm)[:3], vb.rgba(cool)[:3]
    if base is not None:
        b = vb.rgba(base)[:3]
        w = tuple(x + (y - x) * tint for x, y in zip(w, b))
        c = tuple(x + (y - x) * tint for x, y in zip(c, b))
    rgb = [y + (x - y) * t for x, y in zip(w, c)]
    hx, hy, hz = _unit((lx, ly, lz + 1))
    s = highlight * max(0.0, nx * hx + ny * hy + nz * hz) ** shine
    return tuple(255 * (v + (1 - v) * s) for v in rgb)


def torus_mesh(radius, tube, around=112, across=56):
    """A torus as quads `(corners, normal)` in object space, lying in the
    x-z plane round the origin: ring `radius`, tube `tube`."""
    def at(i, j):
        u, v = 2 * math.pi * i / around, 2 * math.pi * j / across
        n = (math.cos(v) * math.cos(u), math.sin(v), math.cos(v) * math.sin(u))
        return tuple(radius * a + tube * b for a, b in zip((math.cos(u), 0, math.sin(u)), n)), n
    quads = []
    for i in range(around):
        for j in range(across):
            pts = [at(i, j), at(i + 1, j), at(i + 1, j + 1), at(i, j + 1)]
            n = _unit(tuple(sum(p[1][k] for p in pts) for k in range(3)))
            quads.append((tuple(p[0] for p in pts), n))
    return quads


def _rotate(v, yaw, pitch, roll):
    x, y, z = v
    c, s = math.cos(yaw), math.sin(yaw)
    x, z = c * x + s * z, -s * x + c * z
    c, s = math.cos(pitch), math.sin(pitch)
    y, z = c * y - s * z, s * y + c * z
    c, s = math.cos(roll), math.sin(roll)
    x, y = c * x - s * y, s * x + c * y
    return x, y, z


def gooch_mesh(cv, quads, cx, cy, yaw=0.0, pitch=0.0, roll=0.0, outline='#101114', width=5, **tone):
    """Draw `quads` (from `torus_mesh`, or any `(corners, normal)` list)
    Gooch-shaded, turned by `yaw`/`pitch`/`roll` radians and centred at
    (cx, cy) in an orthographic view. `outline` draws an ink line `width`
    px round the silhouette, inner edges included (None for none). `tone`
    goes to `gooch_tone` (`light`, `warm`, `cool`, `base`, ...)."""
    faces = []
    for corners, normal in quads:
        n = _rotate(normal, yaw, pitch, roll)
        pts = [_rotate(p, yaw, pitch, roll) for p in corners]
        z = sum(p[2] for p in pts) / len(pts)
        if n[2] > 0:
            faces.append((z, [(cx + x, cy + y) for x, y, _ in pts], gooch_tone(n, **tone)))
        if outline and n[2] < 0:   # the back of a slightly inflated shell peeks out as the outline
            shell = [(cx + x + width * n[0], cy + y + width * n[1]) for x, y, _ in pts]
            faces.append((z + width * n[2], shell, None))
    ink = vb.rgba(outline) if outline else None
    ctx = cv.ctx
    ctx.save()
    ctx.set_line_width(1.5)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    for _, pts, rgb in sorted(faces, key=lambda f: f[0]):
        ctx.new_path()
        for p in pts:
            ctx.line_to(*p)
        ctx.close_path()
        if rgb is None:   # outline: smooth edges, stroked so neighbouring quads leave no gaps
            ctx.set_antialias(cairo.ANTIALIAS_DEFAULT)
            ctx.set_source_rgba(*ink)
            ctx.fill_preserve()
            ctx.stroke()
        else:             # surface: quads share exact edges, so no antialiasing means no seams
            ctx.set_antialias(cairo.ANTIALIAS_NONE)
            ctx.set_source_rgba(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)
            ctx.fill()
    ctx.restore()
    xs = [p[0] for _, pts, _ in faces for p in pts]
    ys = [p[1] for _, pts, _ in faces for p in pts]
    if xs:
        cv.mark('gooch', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


@lru_cache(maxsize=None)
def _torus():
    return torus_mesh(150, 62)


PAPER = '#e9e6df'   # a light ground, so the ink outline reads as it would on a technical drawing


def draw(n, cv):
    p = n / (demo.SECONDS * demo.FPS)
    cv.fill(PAPER)
    gooch_mesh(cv, _torus(), demo.W / 2, demo.H / 2,   # tumbles end over end under a fixed light
               pitch=0.75 + 0.85 * math.pi * p, roll=0.5 - 0.6 * p)


CAPABILITY = Capability(
    id='gooch-shading',
    name='Gooch shading',
    family='camera',
    group='Shader looks',
    aliases=('warm-cool shading', 'Gooch lighting', 'technical illustration shading', 'NPR shading'),
    definition='A 3D object is shaded by colour temperature rather than brightness, going warm yellow '
               'where it faces the light and cool blue where it turns away, with a dark outline round it.',
    phrasings=('shade the shape warm on the lit side and blue on the shadow side instead of going dark',
               'that technical-illustration look where shadows turn cool blue and there is an ink outline',
               'light the object with a yellow-to-blue gradient rather than light-to-black'),
    related=('heat-haze', 'low-poly-faceting', 'thin-film-iridescence', 'cel-shading-look',
             'chrome-specular-shimmer', 'rim-light'),
    api=('videobuilder.capabilities.camera.gooch_shading.gooch_mesh',
         'videobuilder.capabilities.camera.gooch_shading.gooch_tone',
         'videobuilder.capabilities.camera.gooch_shading.torus_mesh'),
    demo=lambda: demo.film(draw),
)
