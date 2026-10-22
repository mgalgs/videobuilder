"""Crane shot: the camera rides the end of a jib arm, so it climbs (or sinks)
along an arc while tilting to keep the subject in frame -- height and angle
change together, and the floor opens up below as the view looks down on it."""
import math
from dataclasses import dataclass

from .. import _demo as demo
from ..schema import Technique
from ... import paths
from ...ease import ease_in_out_quart

NEAR = 0.05  # nothing nearer the lens than this (in world units) is drawn


@dataclass(frozen=True)
class CranePose:
    """Where the camera is and how it looks: `eye` is (x, y, z) in world
    units (y up, z away from the starting camera), `pitch` is the downward
    tilt in radians (0 looks level), `focal` is the lens in frame px."""
    eye: tuple
    pitch: float
    focal: float


def crane_pose(p, target=(0.0, 0.6, 0.0), pivot=(0.0, 1.2, -11.0), arm=6.0, low=-0.05, high=1.05,
               focal=760.0):
    """The camera at progress `p` (0 -> 1) of a crane move: the camera sits on
    the tip of an arm `arm` long hinged at `pivot`, and the arm swings from
    angle `low` to `high` (radians above level, pointing toward +z), so the
    camera rises along an arc. It tilts to keep looking at `target`. Swap
    `low` and `high` (or run `p` 1 -> 0) to crane down."""
    a = low + (high - low) * p
    px, py, pz = pivot
    eye = (px, py + arm * math.sin(a), pz + arm * math.cos(a))
    dy, dz = eye[1] - target[1], target[2] - eye[2]
    return CranePose(eye, math.atan2(dy, dz), focal)


def crane_project(point, pose, center=(demo.W / 2, demo.H / 2)):
    """The world `point` (x, y, z) seen through `pose`: `(sx, sy, depth)` in
    frame px, `depth` its distance along the lens axis (draw larger depths
    first). `None` when it is behind the near plane."""
    x, y, z = (point[i] - pose.eye[i] for i in range(3))
    c, s = math.cos(pose.pitch), math.sin(pose.pitch)
    depth = z * c - y * s
    if depth < NEAR:
        return None
    up = y * c + z * s
    return center[0] + pose.focal * x / depth, center[1] - pose.focal * up / depth, depth


def crane_segment(a, b, pose, center=(demo.W / 2, demo.H / 2)):
    """The world segment a -> b in frame px as `((x0, y0), (x1, y1))`, cut at
    the near plane (for floor lines that pass under the camera), or `None`
    when all of it is behind the lens."""
    def depth(q):
        x, y, z = (q[i] - pose.eye[i] for i in range(3))
        return z * math.cos(pose.pitch) - y * math.sin(pose.pitch)
    da, db = depth(a), depth(b)
    if da < NEAR and db < NEAR:
        return None
    if da < NEAR or db < NEAR:
        t = (NEAR * 1.01 - da) / (db - da)
        cut = tuple(a[i] + (b[i] - a[i]) * t for i in range(3))
        a, b = (cut, b) if da < NEAR else (a, cut)
    pa, pb = crane_project(a, pose, center), crane_project(b, pose, center)
    return pa[:2], pb[:2]


# ---- demo: a pedestal and ball under a gateway, the camera booming up ----
def _shade(hex_, k):
    r, g, b = (int(hex_[i:i + 2], 16) for i in (1, 3, 5))
    return '#%02x%02x%02x' % tuple(max(0, min(255, round(v * k))) for v in (r, g, b))


def _box(x0, x1, y0, y1, z0, z1, color):
    """The faces of an axis-aligned box as (corners, colour, outward normal)."""
    c = lambda x, y, z: (x, y, z)  # noqa: E731
    return [
        ([c(x0, y1, z0), c(x1, y1, z0), c(x1, y1, z1), c(x0, y1, z1)], _shade(color, 1.15), (0, 1, 0)),
        ([c(x0, y0, z0), c(x1, y0, z0), c(x1, y1, z0), c(x0, y1, z0)], _shade(color, 0.85), (0, 0, -1)),
        ([c(x0, y0, z1), c(x1, y0, z1), c(x1, y1, z1), c(x0, y1, z1)], _shade(color, 0.85), (0, 0, 1)),
        ([c(x0, y0, z0), c(x0, y0, z1), c(x0, y1, z1), c(x0, y1, z0)], _shade(color, 0.65), (-1, 0, 0)),
        ([c(x1, y0, z0), c(x1, y0, z1), c(x1, y1, z1), c(x1, y1, z0)], _shade(color, 0.65), (1, 0, 0)),
    ]


_GATE = '#6f7fe0'
_SCENE = (
    _box(-0.6, 0.6, 0.0, 0.7, -0.6, 0.6, '#4a4e5a')            # pedestal
    + _box(-2.3, -2.0, 0.0, 2.5, 1.4, 1.7, _GATE)              # gateway posts and lintel
    + _box(2.0, 2.3, 0.0, 2.5, 1.4, 1.7, _GATE)
    + _box(-2.5, 2.5, 2.5, 2.8, 1.35, 1.75, _GATE)
    + [f for x in (-6.0, -3.6, 3.6, 6.0) for f in _box(x - 0.3, x + 0.3, 0.0, 4.6, 5.0, 5.6, '#2f323b')]
)
_BALL, _BALL_R = (0.0, 1.15, 0.0), 0.45


def _draw(n, cv):
    pose = crane_pose(ease_in_out_quart(demo.phase(n, 0.3, 2.7)))
    for k in range(-12, 13):                                        # floor grid
        for a, b in (((k, 0, -8), (k, 0, 16)), ((-12, 0, k + 4), (12, 0, k + 4))):
            seg = crane_segment(a, b, pose)
            if seg:
                cv.line(*seg[0], *seg[1], demo.LINE, width=2)
    shadow = [crane_project((_BALL_R * 0.9 * math.cos(t), 0.701, _BALL_R * 0.9 * math.sin(t)), pose)
              for t in (i * math.pi / 12 for i in range(24))]
    items = []
    for corners, color, normal in _SCENE:
        centre = tuple(sum(q[i] for q in corners) / 4 for i in range(3))
        if sum(normal[i] * (pose.eye[i] - centre[i]) for i in range(3)) <= 0:
            continue                                                 # faces turned away
        pts = [crane_project(q, pose) for q in corners]
        if all(pts):
            items.append((pts[0][2] + sum(q[2] for q in pts[1:]), 'face', ([q[:2] for q in pts], color)))
    ball = crane_project(_BALL, pose)
    items.append((ball[2] * 4 - 0.4, 'ball', ball))
    for _, kind, it in sorted(items, key=lambda i: -i[0]):
        if kind == 'face':
            paths.draw(cv, it[0], it[1], fill=True)
            if it[1] == _shade('#4a4e5a', 1.15) and all(shadow):
                paths.draw(cv, [q[:2] for q in shadow], '#000000', fill=True, alpha=0.4)
        else:
            r = pose.focal * _BALL_R / it[2]
            demo.dot(cv, it[0], it[1], r=r, color='#e9a91c')
            demo.dot(cv, it[0] - r * 0.3, it[1] - r * 0.32, r=r * 0.35, color='#ffd76a', alpha=0.8)


TECHNIQUE = Technique(
    id='crane-shot',
    name='Crane shot',
    family='camera',
    group='Camera moves',
    aliases=('jib shot', 'boom shot', 'crane up', 'crane down', 'boom up'),
    definition='The camera lifts up through the air in a smooth curve while angling down, '
               'so the subject stays centred but is seen from ever higher above.',
    phrasings=('rise the camera up and look down on the scene',
               'boom up over the subject like the camera is on a big arm',
               'start at eye level and sweep up to a high overhead view'),
    related=('rolling-shutter-wobble', 'punch-in', 'dolly-zoom', 'tilt-shift-miniature', 'morph-cut', 'shake'),
    api=('videobuilder.techniques.camera.crane_shot.crane_pose',
         'videobuilder.techniques.camera.crane_shot.crane_project',
         'videobuilder.techniques.camera.crane_shot.crane_segment',
         'videobuilder.techniques.camera.crane_shot.CranePose'),
    demo=lambda: demo.film(_draw),
)
