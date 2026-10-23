"""Solid Drawing: a form drawn as a real solid, its width, height and depth
fixed while it turns, so every view is the same object seen from another
angle. The demo sets it beside the same turn drawn carelessly, where the box
stretches and shrinks as it goes round and stops reading as one thing."""
import math

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Capability

FOCAL = 900.0
FACES = (  # corner indices, wound so the normal points out of the box
    (0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (3, 2, 6, 7), (0, 3, 7, 4), (1, 5, 6, 2))
TURN = vb.bezier(0.45, 0, 0.55, 1)
LIGHT = (-0.4, -0.8, -0.45)  # towards the light: up, left and in front


def _shade(color, k):
    r, g, b, _ = rgba(color)
    return tuple(round(255 * c * k) for c in (r, g, b))


def box_corners(size, yaw, pitch, roll=0.0):
    """The eight corners of a box `size` = (w, h, d) centred on the origin,
    turned by `yaw` about the vertical, then `pitch` about the horizontal and
    `roll` about the view axis (all in degrees), in view space (+z away)."""
    w, h, d = (s / 2 for s in size)
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    cr, sr = math.cos(math.radians(roll)), math.sin(math.radians(roll))
    out = []
    for x, y, z in ((-w, -h, -d), (w, -h, -d), (w, h, -d), (-w, h, -d),
                    (-w, -h, d), (w, -h, d), (w, h, d), (-w, h, d)):
        x, z = x * cy + z * sy, -x * sy + z * cy
        y, z = y * cp - z * sp, y * sp + z * cp
        x, y = x * cr - y * sr, x * sr + y * cr
        out.append((x, y, z))
    return out


def draw_solid(cv, cx, cy, size, yaw, pitch, color, roll=0.0, focal=FOCAL, edge=None):
    """Draw a box of `size` = (w, h, d) px centred at (cx, cy), turned by
    `yaw`/`pitch`/`roll` degrees and seen through one fixed perspective lens:
    back faces culled, each visible face lit by how squarely it meets a light
    from the upper left, edges stroked in `edge` (default: `color` darkened).
    Keep `size` and `focal` constant across frames and the box keeps its
    volume however it turns. Returns the Box of its screen outline."""
    pts = box_corners(size, yaw, pitch, roll)
    scr = [(cx + x * focal / (focal + z), cy + y * focal / (focal + z)) for x, y, z in pts]
    ln = math.sqrt(sum(c * c for c in LIGHT))
    light = [c / ln for c in LIGHT]
    ctx = cv.ctx
    ctx.save()
    ctx.set_line_join(1)  # round
    for face in FACES:
        a, b, c = (pts[i] for i in face[:3])
        u = [b[i] - a[i] for i in range(3)]
        v = [c[i] - a[i] for i in range(3)]
        nx, ny, nz = v[1] * u[2] - v[2] * u[1], v[2] * u[0] - v[0] * u[2], v[0] * u[1] - v[1] * u[0]
        centre = [sum(pts[i][k] for i in face) / 4 for k in range(3)]
        centre[2] += focal  # the eye sits at z = -focal
        if nx * centre[0] + ny * centre[1] + nz * centre[2] >= 0:
            continue  # faces away from the eye
        nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        lit = max(0.0, (nx * light[0] + ny * light[1] + nz * light[2]) / nl)
        ctx.new_path()
        ctx.move_to(*scr[face[0]])
        for i in face[1:]:
            ctx.line_to(*scr[i])
        ctx.close_path()
        ctx.set_source_rgba(*rgba(_shade(color, 0.45 + 0.55 * lit)))
        ctx.fill_preserve()
        ctx.set_source_rgba(*rgba(edge or _shade(color, 0.3)))
        ctx.set_line_width(2)
        ctx.stroke()
    ctx.restore()
    xs, ys = [p[0] for p in scr], [p[1] for p in scr]
    return vb.Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def _ground(cv, cx, y, r, alpha):
    cv.ctx.save()
    cv.ctx.translate(cx, y)
    cv.ctx.scale(1, 0.16)
    demo.dot(cv, 0, 0, r, color='#000000', alpha=alpha)
    cv.ctx.restore()


def draw(n, cv):
    t = n / demo.FPS
    turn = TURN(demo.phase(n, 0.2, 2.8))
    yaw, pitch = 25 + 200 * turn, 20 + 6 * math.sin(t * 2.1)
    bob = 8 * math.sin(t * 2.4)
    s, mid, floor_y = 140, demo.H / 2 + 10, demo.H / 2 + 150
    cv.line(demo.W / 2, 70, demo.W / 2, demo.H - 60, demo.LINE, width=2)
    lf = demo.font(22, 600)
    for side, cx, solid in (('without', demo.W * 0.27, False), ('with', demo.W * 0.73, True)):
        demo.word(cv, side, cx, 80, font=lf, color=demo.MUTED)
        cv.line(cx - 170, floor_y, cx + 170, floor_y, demo.LINE, width=2)
        _ground(cv, cx, floor_y, 100, 0.45)
        if solid:
            size = (s, s, s)
        else:  # the careless turn: proportions drift with the angle, so it reads as a sprite, not a block
            a = math.radians(yaw)
            size = (s * (1 + 0.45 * math.sin(2 * a)), s * (1 - 0.3 * abs(math.cos(a))), s * (0.45 + 0.5 * turn))
        box = draw_solid(cv, cx, mid + bob, size, yaw, pitch, demo.ACCENT if solid else demo.MUTED)
        cv.mark('solid' if solid else 'loose', *box)


CAPABILITY = Capability(
    id='solid-drawing',
    name='Solid Drawing',
    family='principles',
    group='Classic principles',
    aliases=('3D form consistency', 'volumetric consistency', 'solid form'),
    definition='An object keeps the same size, proportions and perspective as it turns and travels, '
               'so every angle shows one solid thing with real weight and depth.',
    phrasings=('make the box look like a real 3D object as it spins',
               'keep its shape and volume consistent while it rotates',
               'it should feel solid, not like a flat cut-out warping around'),
    related=('beveled-3d-text', 'extrusion', 'outline-to-fill', 'shape-morph', 'extrusion-depth-reveal',
             'volume-preservation'),
    api=('videobuilder.capabilities.principles.solid_drawing.draw_solid',
         'videobuilder.capabilities.principles.solid_drawing.box_corners'),
    demo=lambda: demo.film(draw),
)
