"""Drone flyover: the camera glides forward high above the ground, tipped down
towards it, so fields, a winding river and little buildings stream in from
the horizon and slide away beneath the bottom of the frame, with a gentle
bank as it follows the river's bends."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ..schema import Capability


class DroneCamera:
    """A pinhole camera at `altitude` above a flat ground, at (`x`, `z`) on it
    (z runs forward, x to the right), pitched down by `pitch` radians,
    looking into a `w` x `h` frame with focal length
    `focal` px. `project` maps world points to the screen."""

    def __init__(self, w, h, x=0.0, z=0.0, altitude=260.0, pitch=0.42, focal=None):
        self.w, self.h = w, h
        self.x, self.z, self.altitude = x, z, altitude
        self.pitch = pitch
        self.focal = focal or 0.58 * w

    @property
    def horizon_y(self):
        """Screen y of the horizon before banking."""
        return self.h / 2 - self.focal * math.tan(self.pitch)

    def project(self, x, y, z, near=1.0):
        """World point (x, y, z), y up -> (sx, sy, depth) on screen, before
        banking (banking is applied as a canvas rotation by `drone_flyover`);
        None when the point is closer than `near` or behind the camera."""
        s, c = math.sin(self.pitch), math.cos(self.pitch)
        dy, dz = y - self.altitude, z - self.z
        d = dy * -s + dz * c
        if d < near:
            return None
        up = dy * c + dz * s
        return self.w / 2 + self.focal * (x - self.x) / d, self.h / 2 - self.focal * up / d, d


def _hash(i, j, seed):
    n = (i * 374761393 + j * 668265263 + seed * 1442695041) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65536


def river_x(z, seed=7):
    """World x of the winding river's centre line at forward distance `z`."""
    k = seed * 0.37
    return 300 * math.sin(z / 1100 + k) + 120 * math.sin(z / 430 + 2 * k)


def _poly(cv, pts, color, alpha=1.0):
    c = cv.ctx
    c.new_path()
    c.move_to(pts[0][0], pts[0][1])
    for p in pts[1:]:
        c.line_to(p[0], p[1])
    c.close_path()
    c.set_source_rgba(*vb.rgba(color, alpha))
    c.fill()


def drone_flyover(cv, travel, altitude=420.0, pitch=0.5, follow=0.6, bank=1.0, seed=7, cell=200.0,
                  far=7000.0, sky=kit.BG, haze='#2b3140', fields=('#24302a', '#2c3a2c', '#33372a', '#283327'),
                  river=kit.TEAL, buildings='#7d818b', roofs='#c9c6bd'):
    """Paint the frame a drone sees `travel` world units into its flight over
    a generated landscape: patchwork fields, a winding river and scattered
    block buildings, fading into `haze` towards the horizon. Animate `travel`
    over time to fly forward. The drone drifts sideways to track the river by
    `follow` (0 flies straight, 1 stays over the water) and banks into its
    bends by `bank` (0 stays level). `altitude` and `pitch` (radians down
    from level) set how high it flies and how steeply it looks down; `seed`
    picks the landscape. Returns the `DroneCamera` used."""
    W, H = cv.width, cv.height
    cx = follow * river_x(travel, seed)
    slope = follow * (river_x(travel + 600, seed) - river_x(travel, seed)) / 600
    cam = DroneCamera(W, H, x=cx, z=travel, altitude=altitude, pitch=pitch)
    roll = -bank * math.atan(slope) * 0.5
    fog = lambda d: vb.clamp01((d - far * 0.1) / (far * 0.8)) ** 0.7  # noqa: E731
    shade = lambda col, d, k=1.0: kit.mix(kit.mix(col, '#000000', 1 - k), haze, fog(d))  # noqa: E731

    c = cv.ctx
    c.save()
    c.translate(W / 2, H / 2)
    c.rotate(roll)
    c.translate(-W / 2, -H / 2)
    hy, big = cam.horizon_y, max(W, H)
    grad = cairo.LinearGradient(0, hy - H * 0.6, 0, hy)
    grad.add_color_stop_rgba(0, *vb.rgba(sky))
    grad.add_color_stop_rgba(1, *vb.rgba(haze))
    c.set_source(grad)
    c.rectangle(-big, -big, 3 * big, hy + big + 1)
    c.fill()
    _poly(cv, [(-big, hy), (W + big, hy), (W + big, H + big), (-big, H + big)], haze)

    # Ground: rows far -> near so nearer patches paint over farther ones.
    span = math.ceil(2600 / cell)
    i0 = math.floor(cx / cell)
    j_near, j_far = math.floor(travel / cell), math.ceil((travel + far) / cell)
    boxes = []
    for j in range(j_far, j_near - 1, -1):
        z0, z1 = j * cell, (j + 1) * cell
        for i in range(i0 - span, i0 + span + 1):
            x0, x1 = i * cell, (i + 1) * cell
            corners = [cam.project(x, 0, z) for x, z in ((x0, z0), (x1, z0), (x1, z1), (x0, z1))]
            if None in corners:
                continue
            d = corners[0][2]
            col = fields[int(_hash(i, j, seed) * len(fields))]
            _poly(cv, [p[:2] for p in corners], shade(col, d))
            g = 0.06 * cell  # a hedge line between fields
            inner = [cam.project(x, 0, z) for x, z in ((x0 + g, z0 + g), (x1 - g, z0 + g),
                                                         (x1 - g, z1 - g), (x0 + g, z1 - g))]
            if None not in inner:
                _poly(cv, [p[:2] for p in inner], shade(col, d, 1.12), alpha=0.9)
            r = _hash(j, i, seed + 1)
            mx = (x0 + x1) / 2
            if r < 0.14 and abs(mx - river_x((z0 + z1) / 2, seed)) > cell:
                fw = cell * (0.25 + 0.25 * _hash(i, j, seed + 2))
                fh = cell * (0.15 + 0.5 * _hash(i, j, seed + 3) ** 2)
                boxes.append((j, mx, (z0 + z1) / 2, fw, fh))

    # The river: one ribbon along z, its two banks sampled from near to far.
    step, half = cell / 2, cell * 0.42
    left, right, z = [], [], travel + step
    while z < travel + far:
        a, b = cam.project(river_x(z, seed) - half, 0, z), cam.project(river_x(z, seed) + half, 0, z)
        if a and b:
            left.append(a)
            right.append(b)
        z += step
    if len(left) > 1:
        c.new_path()
        for p in left + right[::-1]:
            c.line_to(p[0], p[1])
        c.close_path()
        g = cairo.LinearGradient(0, left[0][1], 0, left[-1][1])
        for p in left[::4] + left[-1:]:
            g.add_color_stop_rgba((p[1] - left[0][1]) / ((left[-1][1] - left[0][1]) or 1),
                                  *vb.rgba(shade(river, p[2], 0.85)))
        c.set_source(g)
        c.fill()

    # Buildings far -> near, each showing its roof and the faces turned to the camera.
    for _, bx, bz, fw, fh in sorted(boxes, key=lambda b: -b[2]):
        x0, x1, z0, z1 = bx - fw / 2, bx + fw / 2, bz - fw / 2, bz + fw / 2
        v = {(x, y, z): cam.project(x, y, z) for x in (x0, x1) for y in (0, fh) for z in (z0, z1)}
        if None in v.values():
            continue
        d = v[(x0, 0, z0)][2]
        side = x1 if bx < cam.x else x0
        faces = [([(side, 0, z0), (side, 0, z1), (side, fh, z1), (side, fh, z0)], 0.55),
                 ([(x0, 0, z0), (x1, 0, z0), (x1, fh, z0), (x0, fh, z0)], 0.8),
                 ([(x0, fh, z0), (x1, fh, z0), (x1, fh, z1), (x0, fh, z1)], 1.0)]
        for quad, k in faces:
            col = roofs if k == 1.0 else buildings
            _poly(cv, [v[p][:2] for p in quad], shade(col, d, k))
    c.restore()
    return cam


def draw(n, cv):
    t = n / demo.FPS
    travel = 900 * t + 120 * t * t  # cruising, easing a little faster
    drone_flyover(cv, travel, altitude=440 - 30 * t)
    cv.mark('landscape', 0, 0, demo.W, demo.H)


CAPABILITY = Capability(
    id='drone-flyover',
    name='Drone flyover',
    family='camera',
    group='Camera moves',
    aliases=('aerial flyover', 'aerial fly-over', 'drone shot', 'aerial establishing shot'),
    definition='The camera cruises forward high above the ground, angled down, so a wide landscape '
               'pours in from the horizon and slides away underneath it.',
    phrasings=('fly over the landscape like a drone',
               'an aerial shot gliding over fields and a river',
               'swoop forward over the terrain from above'),
    related=('noise-terrain-flyover', 'zoom-to-location-map', 'scale-zoom-through', 'zoom-through',
             'multiplane-camera', 'dolly-zoom'),
    api=('videobuilder.capabilities.camera.drone_flyover.drone_flyover',
         'videobuilder.capabilities.camera.drone_flyover.DroneCamera'),
    demo=lambda: demo.film(draw),
)
