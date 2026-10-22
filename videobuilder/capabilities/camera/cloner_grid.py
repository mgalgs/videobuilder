"""Cloner grid: one block copied into a rows-by-columns array laid out on a
floor in 3D, seen through a camera that orbits it, while a field (here a
ripple out from the centre) drives every copy's height and colour, so the
whole array moves as one surface."""
import math

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Capability

ORBIT = vb.bezier(0.37, 0, 0.63, 1)
LIGHT = (-0.45, 0.8, -0.4)  # towards the light: upper left, in front of the camera at yaw 0


def _mix(a, b, k):
    a, b = rgba(a), rgba(b)
    return tuple(a[i] + (b[i] - a[i]) * k for i in range(3))


def _face_normals():
    return {'top': (0, 1, 0), 'front': (0, 0, -1), 'back': (0, 0, 1), 'left': (-1, 0, 0), 'right': (1, 0, 0)}


def cloner_grid(cv, cols, rows, field, cx=None, cy=None, spacing=90.0, size=62.0, rise=200.0, yaw=30.0,
                pitch=32.0, distance=1500.0, focal=1100.0, color=demo.TEAL, hot=demo.ACCENT, edge=None):
    """Draw `cols` x `rows` copies of a block on a floor plane, as seen by an
    orbiting perspective camera, and return the Box of the drawn grid.

    The copies sit `spacing` px apart, centred on the world origin, each a
    `size` px square column. `field(i, j)` (column `i`, row `j`) gives each
    copy a strength, usually 0 -> 1: the column grows by `rise * strength`
    and its colour moves from `color` towards `hot`; a strength at or below
    -1 hides the copy (for popping clones in). The camera looks at the
    origin from `distance` px away, turned `yaw` degrees around the
    vertical and tilted `pitch` degrees down, projected with `focal` and
    centred on (cx, cy) (default the frame centre). Animate `field` for an
    effector wave, `yaw`/`pitch` for a camera move. Copies are painted far
    to near and lit from the upper left."""
    cx = cv.width / 2 if cx is None else cx
    cy = cv.height / 2 if cy is None else cy
    sy, cy_ = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    sp, cp = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))

    def view(x, y, z):  # world (y up) -> camera space (+z away from the eye, y down on screen)
        x, z = x * cy_ - z * sy, x * sy + z * cy_
        y, z = y * cp + z * sp, -y * sp + z * cp
        return x, -y, z + distance

    def screen(p):
        x, y, z = p
        k = focal / max(z, 1.0)
        return cx + x * k, cy + y * k

    ln = math.sqrt(sum(c * c for c in LIGHT))
    light = tuple(c / ln for c in LIGHT)
    copies = []
    for j in range(rows):
        for i in range(cols):
            s = field(i, j)
            if s <= -1:
                continue
            x = (i - (cols - 1) / 2) * spacing
            z = (j - (rows - 1) / 2) * spacing
            copies.append((view(x, 0, z)[2], i, j, x, z, s))
    copies.sort(reverse=True)  # far first
    eye = (0.0, 0.0, 0.0)
    c = cv.ctx
    c.save()
    c.set_line_join(1)
    xs, ys = [], []
    for _, i, j, x, z, s in copies:
        h = max(2.0, size * 0.5 + rise * max(0.0, s))
        a = size / 2
        base = _mix(color, hot, vb.clamp01(s))
        corners = {
            'top': ((x - a, h, z - a), (x + a, h, z - a), (x + a, h, z + a), (x - a, h, z + a)),
            'front': ((x - a, 0, z - a), (x + a, 0, z - a), (x + a, h, z - a), (x - a, h, z - a)),
            'back': ((x + a, 0, z + a), (x - a, 0, z + a), (x - a, h, z + a), (x + a, h, z + a)),
            'left': ((x - a, 0, z + a), (x - a, 0, z - a), (x - a, h, z - a), (x - a, h, z + a)),
            'right': ((x + a, 0, z - a), (x + a, 0, z + a), (x + a, h, z + a), (x + a, h, z - a)),
        }
        faces = []
        for name, n in _face_normals().items():
            pts = [view(*p) for p in corners[name]]
            centre = [sum(p[k] for p in pts) / 4 for k in range(3)]
            nv = view(*n)
            nv = (nv[0], nv[1], nv[2] - distance)  # a direction: drop the camera offset
            if sum(nv[k] * (centre[k] - eye[k]) for k in range(3)) >= 0:
                continue  # faces away from the eye
            lit = max(0.0, sum(n[k] * light[k] for k in range(3)))
            faces.append((centre[2], pts, 0.42 + 0.58 * lit))
        for _, pts, k in sorted(faces, reverse=True):
            scr = [screen(p) for p in pts]
            xs.extend(p[0] for p in scr)
            ys.extend(p[1] for p in scr)
            c.new_path()
            c.move_to(*scr[0])
            for p in scr[1:]:
                c.line_to(*p)
            c.close_path()
            c.set_source_rgba(*(v * k for v in base), 1.0)
            c.fill_preserve()
            c.set_source_rgba(*(rgba(edge) if edge else tuple(v * 0.35 for v in base) + (1.0,)))
            c.set_line_width(1.5)
            c.stroke()
    c.restore()
    if not xs:
        return vb.Box(cx, cy, 0, 0)
    return vb.Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def draw(n, cv):
    cols, rows = 11, 7
    t = n / demo.FPS
    grow = demo.phase(n, 0.0, 0.8)  # clones pop in from the centre outwards
    wave = demo.phase(n, 0.6, 1.2)  # then the ripple fades up and keeps travelling

    def field(i, j):
        d = math.hypot(i - (cols - 1) / 2, j - (rows - 1) / 2)
        if grow * 7.5 < d:
            return -1
        return wave * (0.5 + 0.5 * math.sin(t * 5.5 - d * 1.1))

    orbit = ORBIT(demo.phase(n, 0.0, demo.SECONDS))  # the camera swings round the array and drops a little
    yaw, pitch = -35 + 70 * orbit, 38 - 10 * orbit
    box = cloner_grid(cv, cols, rows, field, cy=demo.H / 2 + 10, spacing=80, size=56, rise=150, yaw=yaw,
                      pitch=pitch)
    cv.mark('grid', *box)


CAPABILITY = Capability(
    id='cloner-grid',
    name='Cloner grid',
    family='camera',
    group='3D motion',
    aliases=('mograph cloner', 'grid array', 'grid cloner', '3D array', 'instancer grid'),
    definition='A single 3D block is repeated into a grid of rows and columns on a floor, and a moving '
               'wave or field lifts and recolours the copies while the camera circles the whole array.',
    phrasings=('a field of cubes rising and falling in a ripple, seen in 3D',
               'duplicate this block into a big grid and make a wave run through it',
               'a 3D wall of pillars that pulses outward from the middle while the camera orbits'),
    related=('mograph-grid-flip', 'pattern-tiling', 'radial-repeater', 'mosaic-tiling', 'penrose-tiling',
             'small-multiples-cascade'),
    api=('videobuilder.capabilities.camera.cloner_grid.cloner_grid',),
    demo=lambda: demo.film(draw),
)
