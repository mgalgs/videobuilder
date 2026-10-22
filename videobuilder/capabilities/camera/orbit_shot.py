"""Orbit shot: the camera travels round a subject on a circle, always aimed at
it, so the subject stays centred while its sides come round and everything
nearer and farther slides past in opposite directions."""
import math

import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ..schema import Technique


def orbit_shot(p, sweep=math.radians(140), start=math.radians(-70), pitch=math.radians(22), distance=1600,
               focal=1300, target=(0.0, 0.0, 0.0), center=(demo.W / 2, demo.H / 2), ease=vb.bezier(0.45, 0, 0.55, 1)):
    """The camera of an orbit shot at progress `p` (0 -> 1), as a function
    `project(x, y, z) -> (sx, sy, depth)` from world to frame.

    The world has y up and the ground at y = 0. The camera circles `target`
    at `distance`, raised to look down at it by `pitch` radians, and is aimed
    at it throughout, so `target` always lands on `center`. Its heading runs
    from `start` through `sweep` radians (negative to go the other way),
    shaped by `ease`. `focal` is the lens: a point `focal` in front of the
    camera draws at one pixel per world unit. `depth` is the distance in
    front of the camera: skip anything at `depth <= 0`, and draw far to near.

    In a film, drive `p` across the shot and project the scene through it:
    `project = orbit_shot(shot.f / shot_frames)`."""
    yaw = start + sweep * ease(vb.clamp01(p))
    cy_, sy_ = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    tx, ty, tz = target
    cx, cy = center

    def project(x, y, z):
        x, y, z = x - tx, y - ty, z - tz
        xr, zr = x * cy_ - z * sy_, x * sy_ + z * cy_
        yv, zv = y * cp + zr * sp, zr * cp - y * sp
        depth = distance + zv
        s = focal / max(depth, 1e-3)
        return cx + xr * s, cy - yv * s, depth
    return project


# ---- demo: a cube on a grid floor, ringed by pillars, circled by the camera ----

def _box_faces(x, z, w, h, d):
    """The five visible faces (no bottom) of a box standing on the ground at (x, z), as
    (corner points, world normal), corners wound the same way round each."""
    x0, x1, z0, z1 = x - w / 2, x + w / 2, z - d / 2, z + d / 2
    return [
        ([(x0, 0, z0), (x0, h, z0), (x1, h, z0), (x1, 0, z0)], (0, 0, -1)),
        ([(x1, 0, z1), (x1, h, z1), (x0, h, z1), (x0, 0, z1)], (0, 0, 1)),
        ([(x0, 0, z1), (x0, h, z1), (x0, h, z0), (x0, 0, z0)], (-1, 0, 0)),
        ([(x1, 0, z0), (x1, h, z0), (x1, h, z1), (x1, 0, z1)], (1, 0, 0)),
        ([(x0, h, z0), (x0, h, z1), (x1, h, z1), (x1, h, z0)], (0, 1, 0)),
    ]


_LIGHT = (-0.45, 0.8, -0.4)
_PILLARS = [(math.cos(a) * 470, math.sin(a) * 470, c) for a, c in
            ((math.radians(60 * k), (demo.TEAL, kit.MUTED)[k % 2]) for k in range(6))]


def _scene():
    """Every face in the demo scene as (corner points, colour)."""
    faces = []

    def box(x, z, w, h, d, color, front=None):
        for i, (pts, (nx, ny, nz)) in enumerate(_box_faces(x, z, w, h, d)):
            lit = vb.clamp01(0.55 + 0.45 * (nx * _LIGHT[0] + ny * _LIGHT[1] + nz * _LIGHT[2]))
            c = front if (front and i == 0) else color
            faces.append((pts, kit.mix(c, '#000000', 0.55 * (1 - lit))))

    box(0, 0, 240, 240, 240, demo.ACCENT, front=demo.INK)  # the subject, one side marked so the turn reads
    for x, z, c in _PILLARS:
        box(x, z, 70, 170, 70, c)
    return faces


_FACES = _scene()


def _poly(ctx, pts):
    ctx.move_to(*pts[0])
    for q in pts[1:]:
        ctx.line_to(*q)
    ctx.close_path()


def draw(n, cv):
    project = orbit_shot(demo.phase(n, 0.2, 2.8), target=(0, 110, 0))
    ctx = cv.ctx
    # the floor grid
    for i in range(-8, 9):
        for a, b in (((i * 100, -800), (i * 100, 800)), ((-800, i * 100), (800, i * 100))):
            (ax, ay, ad), (bx, by, bd) = project(a[0], 0, a[1]), project(b[0], 0, b[1])
            if ad > 0 and bd > 0:
                ctx.move_to(ax, ay)
                ctx.line_to(bx, by)
    ctx.set_source_rgba(*vb.rgba(demo.LINE))
    ctx.set_line_width(2)
    ctx.stroke()
    # faces facing the camera, far to near
    drawn = []
    for pts, color in _FACES:
        q = [project(*v) for v in pts]
        if min(d for _, _, d in q) <= 0:
            continue
        flat = [(x, y) for x, y, _ in q]
        area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(flat, flat[1:] + flat[:1]))
        if area <= 0:
            continue
        drawn.append((sum(d for _, _, d in q) / len(q), flat, color))
    for _, flat, color in sorted(drawn, key=lambda f: -f[0]):
        _poly(ctx, flat)
        ctx.set_source_rgba(*vb.rgba(color))
        ctx.fill()
    s = 150
    cv.mark('subject', demo.W / 2 - s, demo.H / 2 - s, 2 * s, 2 * s)


TECHNIQUE = Technique(
    id='orbit-shot',
    name='Orbit shot',
    family='camera',
    group='Camera moves',
    aliases=('arc shot', 'circle shot', '360 shot', 'camera orbit', 'turntable camera'),
    definition='The camera swings round a subject on a curved path while staying pointed at it, '
               'so the subject holds the centre as its other sides turn into view and the surroundings sweep past.',
    phrasings=('circle the camera around the product',
               'move the view round the object so we see it from every side',
               'do a slow sweep around the hero while keeping it centred'),
    related=('orbit-loader', 'dolly-zoom', 'orbit', 'zoom-to-location-map', 'two-body-orbit',
             'rolling-shutter-wobble'),
    api=('videobuilder.techniques.camera.orbit_shot.orbit_shot',),
    demo=lambda: demo.film(draw),
)
