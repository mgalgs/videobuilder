"""Tesseract Rotation: a four-dimensional cube turned in a plane that
includes the fourth axis, then flattened to 3D and on to the screen, so its
inner cube swells outward while the outer one shrinks inward and the two
seem to pass through each other."""
import itertools
import math

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Capability

FOCAL = 900.0
W_EYE = 2.6  # distance of the 4D eye from the centre, in half-sizes: smaller makes the inner cube smaller
PLANES = {'xy': (0, 1), 'xz': (0, 2), 'yz': (1, 2), 'xw': (0, 3), 'yw': (1, 3), 'zw': (2, 3)}
TURN = vb.bezier(0.45, 0, 0.55, 1)

VERTICES = tuple(itertools.product((-1, 1), repeat=4))
EDGES = tuple((i, j) for i, j in itertools.combinations(range(16), 2)
              if sum(a != b for a, b in zip(VERTICES[i], VERTICES[j])) == 1)


def tesseract_points(rotations, yaw=0.0, pitch=0.0, w_eye=W_EYE):
    """The 16 corners of a unit tesseract (coordinates +-1) turned by
    `rotations`, a dict of plane name ('xy', 'xz', 'yz', 'xw', 'yw', 'zw') to
    degrees, applied in that order; then projected from 4D to 3D through an eye
    at w = `w_eye`, and turned by `yaw` and `pitch` degrees in 3D. Returns
    `[(x, y, z, w)]`, x/y/z the 3D point (about +-1) and w the rotated fourth
    coordinate before projection."""
    out = []
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    for v in VERTICES:
        p = list(v)
        for plane, deg in rotations.items():
            a, b = PLANES[plane]
            c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
            p[a], p[b] = p[a] * c - p[b] * s, p[a] * s + p[b] * c
        k = 1 / (w_eye - p[3])
        x, y, z = p[0] * k, p[1] * k, p[2] * k
        x, z = x * cy + z * sy, -x * sy + z * cy
        y, z = y * cp - z * sp, y * sp + z * cp
        out.append((x, y, z, p[3]))
    return out


def _mix(c0, c1, t):
    a, b = rgba(c0), rgba(c1)
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(4))


def draw_tesseract(cv, cx, cy, size, rotations, yaw=0.0, pitch=0.0, near=demo.ACCENT, far=demo.TEAL,
                   width=3.0, dots=True, focal=FOCAL, w_eye=W_EYE):
    """Draw a wireframe tesseract centred at (cx, cy), `size` px across its
    outer cube, turned by `rotations` (see `tesseract_points`; animate 'xw',
    'yw' or 'zw' for the 4D turn that makes the cells pass through each other)
    and `yaw`/`pitch` in 3D. Each edge keeps the colour of the cell it starts
    in, `near` for the cell that begins as the outer cube to `far` for the
    one that begins inside, so the eye can follow them trading places; edges
    further away in 3D are drawn thinner and dimmer. Returns the Box of its screen outline."""
    pts = tesseract_points(rotations, yaw, pitch, w_eye)
    scale = size / 2 * (w_eye - 1)  # an unturned outer cube spans `size`
    scr = []
    for x, y, z, _ in pts:
        f = focal / (focal + z * scale)
        scr.append((cx + x * scale * f, cy + y * scale * f, z))
    ctx = cv.ctx
    ctx.save()
    ctx.set_line_cap(1)  # round
    for i, j in sorted(EDGES, key=lambda e: -(scr[e[0]][2] + scr[e[1]][2])):  # far edges first
        depth = vb.clamp01(0.5 - (scr[i][2] + scr[j][2]) / 4)  # 1 near the viewer
        r, g, b, _ = _mix(far, near, (VERTICES[i][3] + VERTICES[j][3]) / 4 + 0.5)
        ctx.set_source_rgba(r, g, b, 0.45 + 0.55 * depth)
        ctx.set_line_width(width * (0.6 + 0.6 * depth))
        ctx.move_to(*scr[i][:2])
        ctx.line_to(*scr[j][:2])
        ctx.stroke()
    ctx.restore()
    if dots:
        for x, y, _ in scr:
            demo.dot(cv, x, y, width * 1.3, color=demo.INK)
    xs, ys = [p[0] for p in scr], [p[1] for p in scr]
    return vb.Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def draw(n, cv):
    t = n / demo.FPS
    turn = TURN(demo.phase(n, 0.3, 2.7))
    box = draw_tesseract(cv, demo.W / 2, demo.H / 2, 210, {'xw': 180 * turn},
                         yaw=28 + 14 * t, pitch=-22)
    cv.mark('tesseract', *box)


CAPABILITY = Capability(
    id='tesseract-rotation',
    name='Tesseract rotation',
    family='camera',
    group='3D motion',
    aliases=('4D hypercube rotation', 'hypercube spin', 'rotating tesseract', '4D cube'),
    definition='A wireframe four-dimensional cube turns through its extra axis, so the small inner cube '
               'swells outward and the big outer cube folds inward until they trade places.',
    phrasings=('a spinning 4D hypercube wireframe',
               'the cube-inside-a-cube that turns itself inside out',
               'rotate a tesseract so its inner and outer cubes swap'),
    related=('tessellation-triangle-flip', 'globe-spin', 'cube-rotate', 'three-d-word-cube', 'spin',
             'rotating-polygon-loop'),
    api=('videobuilder.capabilities.camera.tesseract_rotation.draw_tesseract',
         'videobuilder.capabilities.camera.tesseract_rotation.tesseract_points'),
    demo=lambda: demo.film(draw),
)
