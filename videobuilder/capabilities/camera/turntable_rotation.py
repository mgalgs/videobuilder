"""Turntable rotation: a solid object stands on a round platter and turns
about its upright axis at a steady speed, seen in perspective from a little
above, so its front, sides and back come round to the viewer one after
another."""
import math

import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ..schema import Capability


def turntable_yaw(t, period=3.0, start=0.0, direction=1):
    """The turntable's angle in radians at time `t` seconds: one full turn
    every `period` seconds at constant speed, from `start`. `direction` 1
    turns the near side to the left (anticlockwise seen from above), -1 the
    other way. A clip `period` long loops seamlessly."""
    return start + direction * 2 * math.pi * t / period


class _View:
    """Spin `yaw` about the vertical axis, tip the camera down by `tilt`,
    then a perspective divide at camera distance `distance`; world y is up,
    the viewer looks along +z, and (0, 0, 0) lands on screen (cx, cy)."""

    def __init__(self, cx, cy, yaw, tilt, distance):
        self.cx, self.cy, self.distance = cx, cy, distance
        self.cyaw, self.syaw = math.cos(yaw), math.sin(yaw)
        self.ct, self.st = math.cos(tilt), math.sin(tilt)

    def turn(self, x, y, z):
        """World -> camera space (before the divide)."""
        xr, zr = x * self.cyaw + z * self.syaw, -x * self.syaw + z * self.cyaw
        return xr, y * self.ct + zr * self.st, zr * self.ct - y * self.st

    def __call__(self, x, y, z):
        xc, yc, zc = self.turn(x, y, z)
        f = self.distance / (self.distance + zc)
        return self.cx + xc * f, self.cy - yc * f

    def facing(self, centre, normal):
        """How squarely a face looks at the camera: > 0 visible, 1 head-on."""
        c = self.turn(*centre)
        n = self.turn(*normal)
        to_cam = (-c[0], -c[1], -self.distance - c[2])
        ln = math.sqrt(sum(v * v for v in to_cam)) or 1.0
        return sum(a * b for a, b in zip(n, to_cam)) / ln


def _poly(ctx, pts):
    ctx.new_path()
    ctx.move_to(*pts[0])
    for q in pts[1:]:
        ctx.line_to(*q)
    ctx.close_path()


def _fill(ctx, color):
    ctx.set_source_rgba(*vb.rgba(color))
    ctx.fill()


def _ring(u0, v0, r, n=40):
    return [(u0 + r * math.cos(2 * math.pi * i / n), v0 + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def _rect(u0, v0, u1, v1):
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


def _lens(s):     # the front: a big lens in a rim
    return [(_ring(0, -0.05 * s, 0.62 * s), 'rim'), (_ring(0, -0.05 * s, 0.46 * s), 'dark'),
            (_ring(-0.1 * s, 0.05 * s, 0.16 * s), 'accent')]


def _buttons(s):  # one side: two round buttons
    return [(_ring(0, 0.3 * s, 0.16 * s), 'accent'), (_ring(0, -0.25 * s, 0.16 * s), 'rim')]


def _screen(s):   # the back: a framed screen and a row of keys
    return [(_rect(-0.9 * s, -0.55 * s, 0.55 * s, 0.6 * s), 'dark'),
            (_rect(-0.75 * s, -0.4 * s, 0.4 * s, 0.45 * s), 'glass')] + \
           [(_ring(0.85 * s, v * s, 0.09 * s, 16), 'rim') for v in (0.35, 0, -0.35)]


def _grille(s):   # the other side: slots
    return [(_rect(-0.5 * s, v * s - 0.05 * s, 0.5 * s, v * s + 0.05 * s), 'dark') for v in (0.4, 0.13, -0.13, -0.4)]


# Each side's decoration: a function of the face's half-size in px returning
# (outline in face px, u right / v up as seen from outside, colour role).
SIDES = {'front': _lens, 'right': _buttons, 'back': _screen, 'left': _grille}


def turntable(cv, cx, cy, yaw, size=(250, 160, 120), color='#6c74e0', accent='#f2b33d', platter=True,
              platter_color=demo.LINE, tilt=0.32, distance=1500, sides=SIDES, shadow=True):
    """Draw a box-shaped product `size` = (width, height, depth) px standing
    with its base centre at screen (cx, cy) on a round turntable platter,
    turned `yaw` radians about its vertical axis (see `turntable_yaw`), in
    perspective from `tilt` radians above. Each side carries its own marks
    (`sides`: 'front', 'right', 'back', 'left' -> marks function, as in
    `SIDES`) so every side reads differently as it comes round; faces turned
    away are culled and the rest lit from the upper left. The platter's rim
    ticks turn with the object. Returns the drawn Box."""
    ctx = cv.ctx
    w, h, d = size
    hw, hd = w / 2, d / 2
    at = _View(cx, cy, yaw, tilt, distance)
    pts = []
    if platter:
        r = math.hypot(hw, hd) * 1.35
        n = 72
        top = [at(r * math.cos(2 * math.pi * i / n), 0, r * math.sin(2 * math.pi * i / n)) for i in range(n)]
        low = [at(r * math.cos(2 * math.pi * i / n), -r * 0.09, r * math.sin(2 * math.pi * i / n))
               for i in range(n)]
        if shadow:
            cv.shape_shadow(low, dy=r * 0.08, blur=r * 0.22, color=(0, 0, 0, 0.6))
        for i in range(n):  # the rim: the band between top and bottom circles
            j = (i + 1) % n
            _poly(ctx, [top[i], top[j], low[j], low[i]])
            _fill(ctx, kit.mix(platter_color, '#000000', 0.35))
        _poly(ctx, top)
        _fill(ctx, platter_color)
        ctx.set_line_width(3)
        ctx.set_line_cap(1)
        for k in range(24):  # ticks round the edge, turning with the object
            a = 2 * math.pi * k / 24
            ctx.move_to(*at(r * 0.88 * math.cos(a), 0, r * 0.88 * math.sin(a)))
            ctx.line_to(*at(r * 0.97 * math.cos(a), 0, r * 0.97 * math.sin(a)))
        ctx.set_source_rgba(*vb.rgba(kit.mix(platter_color, '#ffffff', 0.25)))
        ctx.stroke()
        pts += top + low
    elif shadow:
        cv.shape_shadow([at(x, 0, z) for x, z in ((-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd))],
                        dy=h * 0.1, blur=h * 0.25, color=(0, 0, 0, 0.55))

    roles = {'rim': accent, 'accent': accent, 'dark': kit.mix(color, '#000000', 0.7),
             'glass': kit.mix(color, '#ffffff', 0.45)}
    # (name, normal, centre, right, up, half-width, half-height); right = normal x up
    faces = (('front', (0, 0, -1), (0, h / 2, -hd), (1, 0, 0), (0, 1, 0), hw, h / 2),
             ('right', (1, 0, 0), (hw, h / 2, 0), (0, 0, 1), (0, 1, 0), hd, h / 2),
             ('back', (0, 0, 1), (0, h / 2, hd), (-1, 0, 0), (0, 1, 0), hw, h / 2),
             ('left', (-1, 0, 0), (-hw, h / 2, 0), (0, 0, -1), (0, 1, 0), hd, h / 2),
             ('top', (0, 1, 0), (0, h, 0), (1, 0, 0), (0, 0, 1), hw, hd))
    for name, nrm, c, U, V, hu, hv in faces:
        facing = at.facing(c, nrm)
        if facing <= 0:
            continue

        def face(u, v, c=c, U=U, V=V):
            return at(*(c[i] + u * U[i] + v * V[i] for i in range(3)))

        quad = [face(-hu, -hv), face(hu, -hv), face(hu, hv), face(-hu, hv)]
        pts += quad
        _poly(ctx, quad)
        lit = vb.clamp01(0.55 + 0.45 * (nrm[1] * 0.8 + at.turn(*nrm)[0] * -0.6))
        _fill(ctx, kit.mix(color, '#ffffff', 0.18) if name == 'top' else kit.mix(color, '#000000', 0.5 - 0.4 * lit))
        mark = sides.get(name)
        if mark and facing > 0.08:
            for outline, role in mark(min(hu, hv)):
                _poly(ctx, [face(u, v) for u, v in outline])
                _fill(ctx, roles[role])
        if name == 'top':  # a shutter button, so the top reads too
            _poly(ctx, [face(u, v) for u, v in _rect(hw * 0.45, -hd * 0.3, hw * 0.75, hd * 0.3)])
            _fill(ctx, accent)
    xs, ys = zip(*pts)
    return vb.Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def draw(n, cv):
    yaw = turntable_yaw(n / demo.FPS, period=demo.SECONDS, start=math.radians(-28))
    box = turntable(cv, demo.W / 2, demo.H / 2 + 80, yaw)
    cv.mark('object', *box)


CAPABILITY = Capability(
    id='turntable-rotation',
    name='Turntable rotation',
    family='camera',
    group='3D motion',
    aliases=('product spin', '360 spin', 'auto-rotate', 'turntable'),
    definition='A solid object turns round its upright axis at an even pace, as if on a record player, '
               'showing its front, sides and back in turn.',
    phrasings=('spin the product round slowly so we see it from every angle',
               'put the model on a turntable and let it go round',
               'do a full 360 of the object on a rotating stand'),
    related=('globe-spin', 'spin', 'isometric-rotation', 'cube-rotate', 'rotating-polygon-loop',
             'rotating-rings'),
    api=('videobuilder.capabilities.camera.turntable_rotation.turntable',
         'videobuilder.capabilities.camera.turntable_rotation.turntable_yaw'),
    demo=lambda: demo.film(draw),
)
