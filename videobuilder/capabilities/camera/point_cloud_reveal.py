"""Point Cloud Reveal: a 3D form starts as a scatter of dots on its surface; a
scan sweeps across it and, behind the sweep, the dots fill in as a solid,
shaded skin."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def torus(ring=1.0, tube=0.42):
    """A parametric torus for `draw_point_cloud_reveal`: `(u, v)` in 0..1 each
    to a point (x, y, z), lying flat in the x-z plane, `ring` and `tube` its
    two radii in model units."""
    def surface(u, v):
        a, b = u * 2 * math.pi, v * 2 * math.pi
        r = ring + tube * math.cos(b)
        return r * math.cos(a), tube * math.sin(b), r * math.sin(a)
    return surface


def draw_point_cloud_reveal(cv, cx, cy, size, p, surface=None, steps=(96, 40), spin=0.0, tilt=0.55,
                            color=demo.TEAL, dots=demo.INK, dot_radius=2.2, band=0.12, distance=4.0,
                            light=(-0.4, -0.7, 0.6)):
    """Draw `surface` (a parametric `(u, v) -> (x, y, z)`, default `torus()`)
    centred on (cx, cy), one model unit `size` px, revealing at `p` (0 -> 1):
    at 0 it is all dots, one per mesh vertex of a `steps` (u, v) grid; a
    sweep rises bottom to top in model height and, below it, the mesh is a
    solid `color` lit from `light`; at 1 it is all solid. The fill fades in
    over a `band` (fraction of the height) at the sweep's edge. `spin` turns
    it about its vertical axis (radians), `tilt` leans it toward the camera,
    `distance` is the camera distance in model units. Faces are painted back
    to front, so solid parts hide the dots behind them. Returns the Box the
    form covers on screen."""
    surface = surface or torus()
    nu, nv = steps
    cs, ss, ct, st = math.cos(spin), math.sin(spin), math.cos(tilt), math.sin(tilt)
    lx, ly, lz = light
    ll = math.sqrt(lx * lx + ly * ly + lz * lz)
    lx, ly, lz = lx / ll, ly / ll, lz / ll
    base, ink = vb.rgba(color), vb.rgba(dots)

    world = {}
    for i in range(nu):
        for j in range(nv):
            x, y, z = surface(i / nu, j / nv)
            x, z = x * cs + z * ss, -x * ss + z * cs
            y, z = y * ct + z * st, -y * st + z * ct
            world[i, j] = (x, y, z)
    ys = [w[1] for w in world.values()]
    top, bottom = min(ys), max(ys)   # screen y runs down, so `top` is the smallest
    # the sweep's height: below `edge` the skin is solid, fading in across `band` above it
    edge = bottom - (bottom - top) * (1 + band) * vb.clamp01(p) + (bottom - top) * band
    fade = max(1e-6, (bottom - top) * band)

    def screen(w):
        f = distance / (distance - w[2])
        return cx + w[0] * size * f, cy + w[1] * size * f

    faces = []
    for i in range(nu):
        for j in range(nv):
            a, b = world[i, j], world[(i + 1) % nu, j]
            c, d = world[(i + 1) % nu, (j + 1) % nv], world[i, (j + 1) % nv]
            ex, ey, ez = c[0] - a[0], c[1] - a[1], c[2] - a[2]
            fx, fy, fz = d[0] - b[0], d[1] - b[1], d[2] - b[2]
            nx, ny, nz = ey * fz - ez * fy, ez * fx - ex * fz, ex * fy - ey * fx
            nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            depth = (a[2] + b[2] + c[2] + d[2]) / 4
            mid = (a[1] + b[1] + c[1] + d[1]) / 4
            faces.append((depth, mid, (nx / nl, ny / nl, nz / nl), (a, b, c, d)))
    faces.sort(key=lambda f: f[0])

    ctx = cv.ctx
    r = dot_radius * max(0.5, size / 300)
    seen = []
    for depth, mid, (nx, ny, nz), quad in faces:
        pts = [screen(w) for w in quad]
        seen += pts
        solid = vb.clamp01((mid - edge) / fade + 1) if p > 0 else 0.0
        if solid > 0:
            # light whichever side faces the camera, so the inside of the hole shades too
            if nz < 0:
                nx, ny, nz = -nx, -ny, -nz
            lit = 0.35 + 0.65 * max(0.0, nx * lx + ny * ly + nz * lz)
            ctx.move_to(*pts[0])
            for q in pts[1:]:
                ctx.line_to(*q)
            ctx.close_path()
            ctx.set_source_rgba(base[0] * lit, base[1] * lit, base[2] * lit, solid)
            ctx.fill_preserve()
            ctx.set_line_width(0.6)   # seal the seams between neighbouring faces
            ctx.stroke()
        if solid < 1:
            near = vb.clamp01(0.5 + depth / 2.5)   # dots further back are dimmer
            x, y = pts[0]
            ctx.arc(x, y, r, 0, 2 * math.pi)
            ctx.set_source_rgba(ink[0], ink[1], ink[2], (0.35 + 0.65 * near) * (1 - solid))
            ctx.fill()
    xs, ys = [q[0] for q in seen], [q[1] for q in seen]
    return vb.Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def draw(n, cv):
    t = n / demo.FPS
    p = vb.ease_in_out_quart(demo.phase(n, 0.4, 2.6))
    box = draw_point_cloud_reveal(cv, demo.W / 2, demo.H / 2 - 30, 180, p, spin=0.6 + 0.35 * t, tilt=0.6)
    cv.mark('form', *box)


CAPABILITY = Capability(
    id='point-cloud-reveal',
    name='Point cloud reveal',
    family='camera',
    group='3D motion',
    aliases=('point-cloud build', 'particle scan'),
    definition='A 3D object first appears only as a lattice of dots on its surface, then a sweep fills '
               'those dots in until it stands as a solid, shaded form.',
    phrasings=('the 3D model starts as dots and fills in to a solid surface',
               'scan the object in from a point cloud',
               'show the shape as a dotted wireframe that resolves into the finished model'),
    related=('particle-morph', 'scatter-plot-point-appear', 'ripple', 'location-ripple-pulse',
             'image-to-particles', 'smoke-dissolve'),
    api=('videobuilder.capabilities.camera.point_cloud_reveal.draw_point_cloud_reveal',
         'videobuilder.capabilities.camera.point_cloud_reveal.torus'),
    demo=lambda: demo.film(draw),
)
