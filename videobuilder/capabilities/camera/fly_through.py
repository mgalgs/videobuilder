"""Fly-through: the camera travels along a path through a little 3D world --
down a road, between pillars, under arches -- so near things sweep past the
edges of the frame while far things slowly grow out of the haze ahead.

A tiny flat-shaded projector: world boxes and ground quads, a pinhole camera
placed on a path, near-plane clipping, painter's ordering and depth fog. Y is
up, the camera looks down +z when its heading is 0."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

NEAR = 0.05


def look_at(eye, target):
    """The camera basis `(eye, right, up, forward)` for a camera at `eye`
    looking at `target` (both `(x, y, z)`), kept level (no roll)."""
    fx, fy, fz = (t - e for t, e in zip(target, eye))
    d = math.sqrt(fx * fx + fy * fy + fz * fz) or 1.0
    f = (fx / d, fy / d, fz / d)
    rx, rz = f[2], -f[0]                       # right = up(0,1,0) x forward, flattened
    rd = math.hypot(rx, rz) or 1.0
    r = (rx / rd, 0.0, rz / rd)
    u = (f[1] * r[2] - f[2] * r[1], f[2] * r[0] - f[0] * r[2], f[0] * r[1] - f[1] * r[0])
    u = u if u[1] >= 0 else tuple(-c for c in u)
    return eye, r, u, f


def to_camera(camera, point):
    """`point` in camera space `(x right, y up, z depth)`."""
    eye, r, u, f = camera
    d = [p - e for p, e in zip(point, eye)]
    dot = lambda a: a[0] * d[0] + a[1] * d[1] + a[2] * d[2]  # noqa: E731
    return dot(r), dot(u), dot(f)


def _clip_near(poly, near=NEAR):
    out = []
    for i, a in enumerate(poly):
        b = poly[(i + 1) % len(poly)]
        if a[2] >= near:
            out.append(a)
        if (a[2] >= near) != (b[2] >= near):
            t = (near - a[2]) / (b[2] - a[2])
            out.append(tuple(a[k] + (b[k] - a[k]) * t for k in range(3)))
    return out


def _mix(color, other, t):
    a, b = vb.rgba(color), vb.rgba(other)
    return tuple(x + (y - x) * t for x, y in zip(a[:3], b[:3]))


def box_faces(x0, y0, z0, x1, y1, z1, color):
    """The six faces of an axis-aligned box as `(corners, normal, color)`."""
    c = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    quads = (((0, 1, 3, 2), (-1, 0, 0)), ((4, 6, 7, 5), (1, 0, 0)), ((0, 4, 5, 1), (0, -1, 0)),
             ((2, 3, 7, 6), (0, 1, 0)), ((0, 2, 6, 4), (0, 0, -1)), ((1, 5, 7, 3), (0, 0, 1)))
    return [([c[i] for i in q], n, color) for q, n in quads]


def draw_world(cv, camera, boxes=(), ground=(), focal=None, fog=60.0, haze=demo.BG,
               light=(-0.45, 0.8, -0.35)):
    """Draw a world seen from `camera` (see `look_at`). `ground` is a list of
    flat `(corners, color)` polygons painted first, in order (roads, lane
    marks); `boxes` is a list of `(x0, y0, z0, x1, y1, z1, color)` sorted far
    to near and flat-shaded by `light`. Everything fades into `haze` towards
    `fog` units away. `focal` defaults to the frame width (about a 53 degree
    horizontal field of view)."""
    W, H = cv.width, cv.height
    focal = focal or W
    eye = camera[0]
    L = math.sqrt(sum(c * c for c in light))
    light = tuple(c / L for c in light)

    def poly(corners, color, shade=1.0):
        pts = _clip_near([to_camera(camera, p) for p in corners])
        if len(pts) < 3:
            return
        depth = sum(p[2] for p in pts) / len(pts)
        fade = vb.clamp01(depth / fog) ** 0.8
        rgb = _mix(color, '#000000', 1 - shade)
        rgb = tuple(x + (y - x) * fade for x, y in zip(rgb, vb.rgba(haze)[:3]))
        rgb = tuple(255 * c for c in rgb)
        vb.paths.draw(cv, [(W / 2 + x * focal / z, H / 2 - y * focal / z) for x, y, z in pts], rgb, fill=True)

    for corners, color in ground:
        poly(corners, color)
    centre = lambda b: ((b[0] + b[3]) / 2 - eye[0]) ** 2 + ((b[2] + b[5]) / 2 - eye[2]) ** 2  # noqa: E731
    for b in sorted(boxes, key=centre, reverse=True):
        for corners, n, color in box_faces(*b):
            face = [sum(c[k] for c in corners) / 4 for k in range(3)]
            to_eye = [e - f for e, f in zip(eye, face)]
            if sum(a * b_ for a, b_ in zip(n, to_eye)) <= 0:
                continue  # back face
            lit = 0.55 + 0.45 * max(0.0, sum(a * b_ for a, b_ in zip(n, light)))
            poly(corners, color, lit)


def path_camera(path, s, height=1.2, ahead=4.0, tilt=0.15):
    """A camera riding `path(s) -> (x, z)` at distance `s`, `height` above the
    ground, aimed at the path `ahead` units further on (and `tilt` lower), so
    it banks its gaze into the curves like a driver."""
    x, z = path(s)
    tx, tz = path(s + ahead)
    return look_at((x, height, z), (tx, height - tilt, tz))


def fly_through(cv, path, boxes, p, length, ground=(), start=0.0, **kw):
    """Draw a fly-through at progress `p` (0 -> 1): the camera travels
    `length` units along `path(s) -> (x, z)` from `start`, through `boxes` and
    over `ground` (see `draw_world`). `kw` goes to `path_camera` (`height`,
    `ahead`, `tilt`) or `draw_world` (`focal`, `fog`, `haze`, `light`).

    In a film, drive `p` across the shot: `fly_through(cv, road, city, shot.f / shot_frames, 40)`."""
    cam_kw = {k: kw.pop(k) for k in ('height', 'ahead', 'tilt') if k in kw}
    draw_world(cv, path_camera(path, start + length * p, **cam_kw), boxes, ground, **kw)


def road(path, s0, s1, width=3.0, step=0.5, color=demo.LINE, dash=None, dash_len=0.6, dash_gap=0.9):
    """Ground quads for a road of `width` following `path` from `s0` to `s1`,
    plus a dashed centre line in `dash` colour when given (for `draw_world`)."""
    def edge(s, off):
        x, z = path(s)
        x2, z2 = path(s + 0.01)
        tx, tz = x2 - x, z2 - z
        d = math.hypot(tx, tz) or 1.0
        return (x + tz / d * off, 0.0, z - tx / d * off)
    out, s = [], s0
    while s < s1:
        e = min(s + step, s1)
        out.append(([edge(s, -width / 2), edge(s, width / 2), edge(e, width / 2), edge(e, -width / 2)], color))
        s = e
    if dash:
        s = s0
        while s < s1:
            e = s + dash_len
            out.append(([edge(s, -0.06), edge(s, 0.06), edge(e, 0.06), edge(e, -0.06)], dash))
            s = e + dash_gap
    return out


# ---- demo: down a winding road through a city of arches and blocks ----
def _path(s):
    return 2.2 * math.sin(s * 0.11) + 1.2 * math.sin(s * 0.047 + 1.0), s


_GATE = '#7d86e8'
_BLOCK = '#5f68c9'


def _world():
    boxes = []
    for i in range(3, 26):
        s = i * 3.2
        x, z = _path(s)
        if i % 2 == 0:  # an arch straddling the road
            boxes += [(x - 2.4, 0, z - 0.25, x - 1.9, 3.2, z + 0.25, _GATE),
                      (x + 1.9, 0, z - 0.25, x + 2.4, 3.2, z + 0.25, _GATE),
                      (x - 2.4, 3.2, z - 0.25, x + 2.4, 3.8, z + 0.25, _GATE)]
        for side in (-1, 1):  # blocks set back either side
            h = 1.2 + 2.5 * (0.5 + 0.5 * math.sin(i * 2.3 + side))
            off = 3.4 + 1.2 * (0.5 + 0.5 * math.sin(i * 1.7 - side))
            boxes.append((x + side * off - 0.8, 0, z - 0.8, x + side * off + 0.8, h, z + 0.8, _BLOCK))
    return boxes, road(_path, 0, 90, width=3.4, color='#262a36', dash=demo.ACCENT)


_WORLD = _world()


def _draw(n, cv):
    boxes, ground = _WORLD
    cv.rect(0, cv.height / 2, cv.width, cv.height / 2, '#191b22')
    p = demo.phase(n, 0, demo.SECONDS)
    p = 0.15 * p + 0.85 * (0.5 - 0.5 * math.cos(math.pi * p))  # already moving at the start, a touch slower at the ends
    fly_through(cv, _path, boxes, p, 30, ground=ground, start=2.0, fog=45, height=1.1)


TECHNIQUE = Technique(
    id='fly-through',
    name='Fly-through',
    family='camera',
    group='Camera moves',
    aliases=('walkthrough', 'fly-in', 'flythrough'),
    definition='The camera glides forward along a route through a 3D space, slipping between and '
               'under the objects around it as they rush past the edges of the frame.',
    phrasings=('fly the camera down the street between the buildings',
               'move through the scene as if we are travelling inside it',
               'a first-person glide through the 3D world, passing under the arches'),
    related=('zoom-through', 'noise-terrain-flyover', 'zoom-to-location-map', 'scale-zoom-through',
             'object-pass-through', 'follow-through'),
    api=('videobuilder.techniques.camera.fly_through.fly_through',
         'videobuilder.techniques.camera.fly_through.draw_world',
         'videobuilder.techniques.camera.fly_through.path_camera',
         'videobuilder.techniques.camera.fly_through.look_at',
         'videobuilder.techniques.camera.fly_through.road'),
    demo=lambda: demo.film(_draw),
)
