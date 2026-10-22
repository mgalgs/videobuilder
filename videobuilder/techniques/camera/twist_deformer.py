"""Twist deformer: every slice of a 3D form is turned about its upright axis
by an angle that grows from the base to the top, so a straight block winds
up like a wrung towel and can unwind again."""
import math

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Technique


def twist(points, angle, bottom, top, ease=None):
    """3D `points` (x, y, z), y up, each turned about the y axis by `angle`
    radians times its height fraction between `bottom` (no turn) and `top`
    (the full `angle`); heights outside that range are clamped. `ease` maps
    the fraction 0 -> 1 first (default linear), e.g. `vb.ease_in_quad` to
    keep the twist near the top."""
    span = (top - bottom) or 1.0
    out = []
    for x, y, z in points:
        t = vb.clamp01((y - bottom) / span)
        a = angle * (ease(t) if ease else t)
        c, s = math.cos(a), math.sin(a)
        out.append((x * c - z * s, y, x * s + z * c))
    return out


def _shade(color, k):
    r, g, b, a = rgba(color)
    return (min(1.0, r * k), min(1.0, g * k), min(1.0, b * k), a)


def _box_quads(w, h, d, rows, cols):
    """The box's surface in model space as (side quads, cap quads): the four
    sides cut into `rows` x `cols` so they can bend, plus the two caps."""
    hw, hh, hd = w / 2, h / 2, d / 2
    corners = [(-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)]  # (x, z) round the base
    quads = []
    for i in range(4):
        (x0, z0), (x1, z1) = corners[i], corners[(i + 1) % 4]
        for c in range(cols):
            u0, u1 = c / cols, (c + 1) / cols
            xa, za = x0 + (x1 - x0) * u0, z0 + (z1 - z0) * u0
            xb, zb = x0 + (x1 - x0) * u1, z0 + (z1 - z0) * u1
            for r in range(rows):
                y0, y1 = -hh + h * r / rows, -hh + h * (r + 1) / rows
                quads.append([(xa, y0, za), (xb, y0, zb), (xb, y1, zb), (xa, y1, za)])
    caps = [[(x, y, z) for x, z in corners] for y in (-hh, hh)]
    return quads, caps


def twisted_box(cv, cx, cy, w, h, d, angle, color, spin=0.0, tilt=0.35, rows=28, cols=3,
                distance=1000, ease=None, grid=0.22, alpha=1.0):
    """Draw a `w` x `h` x `d` px box standing on end, centred at (cx, cy),
    twisted by `angle` radians from its base (no turn) to its top, lit and in
    perspective. `spin` turns the whole box about its upright axis and `tilt`
    tips the camera down onto its top (radians). The sides are cut into
    `rows` x `cols` facets so they curve; `grid` is the strength of the faint
    facet lines that show the wind. `ease` goes to `twist`. Returns the Box
    of the drawn form."""
    cs, ss, ct, st = math.cos(spin), math.sin(spin), math.cos(tilt), math.sin(tilt)
    light = (-0.45, 0.6, -0.66)  # from the upper left, in front

    def view(p):  # spin about y, then tip about x so the top leans towards the camera
        x, y, z = p
        x, z = x * cs - z * ss, x * ss + z * cs
        return x, y * ct + z * st, -y * st + z * ct

    def project(p):
        x, y, z = p
        f = distance / (distance + z)
        return cx + x * f, cy - y * f

    sides, caps = _box_quads(w, h, d, rows, cols)
    faces = []
    for quad, cap in [(q, None) for q in sides] + [(q, i) for i, q in enumerate(caps)]:
        model = twist(quad, angle, -h / 2, h / 2, ease)
        v = [view(p) for p in model]
        (ax, ay, az), (bx, by, bz), (qx, qy, qz) = v[0], v[1], v[3]
        ux, uy, uz, wx, wy, wz = bx - ax, by - ay, bz - az, qx - ax, qy - ay, qz - az
        nx, ny, nz = uy * wz - uz * wy, uz * wx - ux * wz, ux * wy - uy * wx
        mx, my, mz = (sum(p[k] for p in v) / 4 for k in range(3))
        if cap is None:  # a side points away from the axis at its own height
            out = view((sum(p[0] for p in model) / 4, 0, sum(p[2] for p in model) / 4))
        else:
            out = view((0, 1 if cap else -1, 0))
        if nx * out[0] + ny * out[1] + nz * out[2] < 0:
            nx, ny, nz = -nx, -ny, -nz
        ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        nx, ny, nz = nx / ln, ny / ln, nz / ln
        if nx * mx + ny * my + nz * (mz + distance) >= 0:  # faces away from the camera
            continue
        k = 0.42 + 0.75 * max(0.0, nx * light[0] + ny * light[1] + nz * light[2])
        faces.append((mx * mx + my * my + (mz + distance) ** 2, [project(p) for p in v], k))

    ctx = cv.ctx
    pts = []
    with cv.layer(opacity=alpha):
        for _, quad, k in sorted(faces, key=lambda f: -f[0]):
            ctx.new_path()
            ctx.move_to(*quad[0])
            for p in quad[1:]:
                ctx.line_to(*p)
            ctx.close_path()
            ctx.set_source_rgba(*_shade(color, k))
            ctx.fill_preserve()
            ctx.set_line_width(1.0)
            ctx.stroke_preserve()  # same colour: hides the seams between facets
            if grid:
                ctx.set_source_rgba(*_shade(color, k * 0.55)[:3], grid)
                ctx.stroke()
            ctx.new_path()
            pts.extend(quad)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return vb.Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def draw(n, cv):
    t = n / demo.FPS
    wind = vb.ease_in_out_quart(demo.phase(n, 0.3, 1.5))
    unwind = vb.ease_in_out_quart(demo.phase(n, 1.8, 2.8))
    angle = math.radians(200) * wind - math.radians(260) * unwind  # wring one way, then past straight
    cx, cy, w, h = demo.W / 2, demo.H / 2 + 6, 120, 290
    cv.ctx.save()
    cv.ctx.translate(cx, cy + h / 2 + 18)
    cv.ctx.scale(1, 0.18)
    demo.dot(cv, 0, 0, 110, color='#000000', alpha=0.35)
    cv.ctx.restore()
    box = twisted_box(cv, cx, cy, w, h, 120, angle, '#e8b21c', spin=0.5 + 0.12 * t, tilt=0.32)
    cv.mark('box', *box)


TECHNIQUE = Technique(
    id='twist-deformer',
    name='Twist deformer',
    family='camera',
    group='3D motion',
    aliases=('twist modifier', 'twist deform', 'wring twist'),
    definition='A solid block winds round its own upright axis, each level turned a little more '
               'than the one below, so it spirals up like a wrung-out cloth and then unwinds.',
    phrasings=('wring the box like a towel so it corkscrews',
               'twist the column so the top turns but the base stays put',
               'make the 3D block spiral around itself and then straighten out'),
    related=('confetti', 'swirl', 'arc-bend-morph', 'origami-fold', 'globe-spin',
             'line-to-polygon-transform'),
    api=('videobuilder.techniques.camera.twist_deformer.twisted_box',
         'videobuilder.techniques.camera.twist_deformer.twist'),
    demo=lambda: demo.film(draw),
)
