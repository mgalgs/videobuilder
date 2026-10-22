"""POV shot: the camera is the character's eyes, so the frame shows the world
from their head height as they walk -- the picture bobs with each step, the
gaze drifts, and their own hands sit at the bottom edge of the frame."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def pov_eye(distance, height=1.6, stride=1.5, bob=0.05, sway=0.035, roll=0.012):
    """The eye of someone who has walked `distance` world units forward ->
    `(x, y, z, roll)`: one dip of `bob` per step of `stride`, a side-to-side
    `sway` over each pair of steps, and a slight head `roll` with it. Hand it
    to `pov_project` as the camera position."""
    step = distance / stride * math.pi
    return (sway * math.sin(step),
            height - bob * abs(math.sin(step)),
            distance,
            roll * math.sin(step))


def pov_project(point, eye, size, yaw=0.0, pitch=0.0, fov=80.0, near=0.05):
    """World `point` (x right, y up, z forward) seen from `eye` (as from
    `pov_eye`) looking along +z, turned by `yaw` and tilted by `pitch` radians,
    on a frame of `size` (w, h) with horizontal field of view `fov` degrees ->
    screen `(sx, sy)`, or None when the point is behind the eye."""
    ex, ey, ez, er = eye
    x, y, z = point[0] - ex, point[1] - ey, point[2] - ez
    x, z = math.cos(yaw) * x - math.sin(yaw) * z, math.sin(yaw) * x + math.cos(yaw) * z
    y, z = math.cos(pitch) * y - math.sin(pitch) * z, math.sin(pitch) * y + math.cos(pitch) * z
    if z < near:
        return None
    w, h = size
    f = w / 2 / math.tan(math.radians(fov) / 2)
    px, py = f * x / z, -f * y / z
    px, py = math.cos(er) * px - math.sin(er) * py, math.sin(er) * px + math.cos(er) * py
    return w / 2 + px, h / 2 + py


# -- demo: walking down a hall of gates ---------------------------------------

GATE_GAP, HALF, POST, TALL = 3.0, 1.6, 0.35, 3.0
PILLAR, PILLAR_SIDE, LINTEL = '#8a8cf0', '#6366c4', '#a3a5ff'


def _quad(cv, pts, color):
    if any(p is None for p in pts):
        return
    ctx = cv.ctx
    ctx.set_source_rgba(*vb.canvas.rgba(color))
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()
    ctx.fill()


def _gate(cv, z, see):
    d = POST
    for side in (-1, 1):
        inner, outer = side * HALF, side * (HALF + d)
        _quad(cv, [see((inner, 0, z)), see((inner, TALL, z)), see((inner, TALL, z + d)), see((inner, 0, z + d))],
              PILLAR_SIDE)
        _quad(cv, [see((inner, 0, z)), see((outer, 0, z)), see((outer, TALL, z)), see((inner, TALL, z))], PILLAR)
    _quad(cv, [see((-HALF - d, TALL, z)), see((HALF + d, TALL, z)), see((HALF + d, TALL + d, z)),
               see((-HALF - d, TALL + d, z))], LINTEL)


def _hand(cv, cx, cy, side):
    demo.dot(cv, cx, cy + 40, 46, color='#d9a23a')               # sleeve
    cv.rect(cx - 38, cy - 44, 76, 70, demo.INK, radius=30)        # fist
    cv.rect(cx - 11 - 29 * side, cy - 30, 22, 40, '#c9cbd1', radius=11)  # thumb, on the inside


def draw(n, cv):
    t = n / demo.FPS
    walked = 1.35 * t  # a steady walking pace
    eye = pov_eye(walked)
    look = demo.phase(n, 1.6, 2.6)
    yaw = 0.16 * math.sin(math.pi * look) * (1 - 0.4 * look)  # glance to the right and back
    size = (demo.W, demo.H)
    see = lambda p: pov_project(p, eye, size, yaw=yaw, pitch=-0.03)  # noqa: E731

    horizon = see((0, eye[1], walked + 1000))
    hy = horizon[1] if horizon else demo.H / 2
    cv.rect(-200, hy, demo.W + 400, demo.H, '#1d1f26')         # floor
    end = walked + 40
    _quad(cv, [see((-HALF, 0, end)), see((HALF, 0, end)), see((HALF, TALL, end)), see((-HALF, TALL, end))],
          '#0b0c10')
    first = math.floor(walked / GATE_GAP) + 1
    for k in range(first + 12, first - 1, -1):                    # far to near, so near gates cover far ones
        z = k * GATE_GAP
        if z - walked < 0.3:
            continue
        z0, z1 = z + GATE_GAP * 0.25, z + GATE_GAP * 0.55          # a dash down the middle of the floor
        _quad(cv, [see((-0.08, 0, z0)), see((0.08, 0, z0)), see((0.08, 0, z1)), see((-0.08, 0, z1))], '#f1b434')
        _gate(cv, z, see)

    step = walked / 1.5 * math.pi                                  # the hands swing with the steps
    for side in (-1, 1):
        swing = 10 * math.sin(step) * side
        _hand(cv, demo.W / 2 + side * 300, demo.H - 30 + swing + 6 * abs(math.sin(step)), side)
    cv.mark('hands', demo.W / 2 - 350, demo.H - 120, 700, 120)


TECHNIQUE = Technique(
    id='pov-shot',
    name='POV shot',
    family='camera',
    group='Camera moves',
    aliases=('point-of-view shot', 'first-person camera', 'first-person view', 'subjective camera'),
    definition='The camera sits where a character\'s eyes are and moves as their head does, '
               'so the audience sees the scene exactly as that character does.',
    phrasings=('show it from the walker\'s own eyes',
               'make it first person, like we are the one walking',
               'let the viewer see what the character is seeing'),
    related=('ui-walkthrough-camera-zoom', 'zoom-through', 'match-cut', 'focus-breathing',
             'cctv-surveillance-look', 'virtual-first-down-line'),
    api=('videobuilder.techniques.camera.pov_shot.pov_project',
         'videobuilder.techniques.camera.pov_shot.pov_eye'),
    demo=lambda: demo.film(draw),
)
