"""Isometric Rotation: a box drawn in isometric projection turns about its
vertical axis a quarter at a time, pausing between turns, so each side
comes round to face the viewer in turn while the view itself never tilts."""
import math

import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ..schema import Capability

COS30, SIN30 = math.cos(math.pi / 6), 0.5


def iso_point(x, y, z, yaw, cx, cy):
    """World point (x, y, z) -- y up, the object spun `yaw` radians about the
    vertical axis -- in isometric projection, with the world origin at screen
    (cx, cy). One world unit is one pixel along each axis."""
    c, s = math.cos(yaw), math.sin(yaw)
    xr, zr = x * c - z * s, x * s + z * c
    return cx + (xr - zr) * COS30, cy + (xr + zr) * SIN30 - y


def stepped_turns(p, steps=4, turn=0.65, step=math.pi / 2, ease=vb.ease_in_out_quart):
    """Yaw at progress `p` (0 -> 1) for `steps` turns of `step` radians each,
    one per equal slot: the turn eases through the first `turn` fraction of
    its slot and holds still for the rest."""
    p = vb.clamp01(p)
    k = min(int(p * steps), steps - 1)
    local = vb.clamp01((p * steps - k) / turn)
    return step * (k + ease(local))


def _poly(ctx, pts, closed=True):
    ctx.move_to(*pts[0])
    for q in pts[1:]:
        ctx.line_to(*q)
    if closed:
        ctx.close_path()


def _ring(u0, v0, r, n=40):
    return [(u0 + r * math.cos(2 * math.pi * i / n), v0 + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


# Face marks in face coordinates: u runs -1 (left) -> 1 (right) as the face is
# seen, v -1 (bottom) -> 1 (top). Each mark is (points, closed, filled).
MARKS = {
    'ring': [(_ring(0, 0, 0.5), True, False)],
    'bars': [([(-0.5, v), (0.5, v)], False, False) for v in (0.35, 0, -0.35)],
    'dots': [([(u - 0.14, v - 0.14), (u + 0.14, v - 0.14), (u + 0.14, v + 0.14), (u - 0.14, v + 0.14)], True, True)
             for u in (-0.25, 0.25) for v in (-0.25, 0.25)],
    'tri': [([(-0.5, -0.4), (0.5, -0.4), (0, 0.45)], True, False)],
}


def isometric_box(cv, cx, cy, size, yaw, color=demo.TEAL, height=None, marks=('ring', 'bars', 'dots', 'tri'),
                  mark_color=demo.BG, fill_color=demo.ACCENT, line_width=8, shadow=True):
    """Draw a box standing on the floor point (cx, cy), `size` pixels wide
    and deep and `height` tall (default: a cube), spun `yaw` radians about
    its vertical axis, in isometric projection. Its four sides carry `marks`
    (names from `MARKS`, or None for a plain side) so a turn reads; the top
    carries a small arrow pointing along the box's own +x. Sides facing away
    are culled and the rest shaded by how squarely they face the viewer."""
    ctx = cv.ctx
    hs, h = size / 2, size if height is None else height

    def at(x, y, z):
        return iso_point(x, y, z, yaw, cx, cy)

    if shadow:
        base = [at(x, 0, z) for x, z in ((-hs, -hs), (hs, -hs), (hs, hs), (-hs, hs))]
        cv.shape_shadow(base, dy=size * 0.08, blur=size * 0.18, color=(0, 0, 0, 0.55))
    c, s = math.cos(yaw), math.sin(yaw)
    for i, (nx, nz) in enumerate(((1, 0), (0, 1), (-1, 0), (0, -1))):
        nxr, nzr = nx * c - nz * s, nx * s + nz * c
        facing = (nxr + nzr) / math.sqrt(2)  # 1: square to the viewer, 0: edge-on
        if facing <= 1e-4:
            continue
        lit = vb.clamp01(0.5 + 0.5 * (nzr - nxr))  # light from the upper left
        tx, tz = nz, -nx  # the face's left-to-right direction, as seen

        def face(u, v):
            return at(hs * (nx + u * tx), h / 2 * (1 + v), hs * (nz + u * tz))

        _poly(ctx, [face(-1, -1), face(1, -1), face(1, 1), face(-1, 1)])
        ctx.set_source_rgba(*vb.rgba(kit.mix(color, '#000000', 0.42 - 0.3 * lit)))
        ctx.fill()
        name = marks[i % len(marks)] if marks and facing > 0.12 else None  # none on a near-edge-on side
        for pts, closed, filled in MARKS.get(name, ()):
            _poly(ctx, [face(u, v) for u, v in pts], closed)
            if filled:
                ctx.set_source_rgba(*vb.rgba(fill_color))
                ctx.fill()
            else:
                ctx.set_source_rgba(*vb.rgba(mark_color))
                ctx.set_line_width(line_width)
                ctx.set_line_cap(1)  # round
                ctx.set_line_join(1)
                ctx.stroke()
    top = [at(x, h, z) for x, z in ((-hs, -hs), (hs, -hs), (hs, hs), (-hs, hs))]
    _poly(ctx, top)
    ctx.set_source_rgba(*vb.rgba(kit.mix(color, '#ffffff', 0.28)))
    ctx.fill()
    arrow = [(-0.5, -0.12), (0.1, -0.12), (0.1, -0.32), (0.55, 0), (0.1, 0.32), (0.1, 0.12), (-0.5, 0.12)]
    _poly(ctx, [at(hs * u, h, hs * w) for u, w in arrow])
    ctx.set_source_rgba(*vb.rgba(mark_color))
    ctx.fill()
    xs, ys = zip(*(top + [at(x, 0, z) for x, z in ((-hs, -hs), (hs, -hs), (hs, hs), (-hs, hs))]))
    return vb.Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def draw(n, cv):
    cx, cy, size = demo.W / 2, demo.H / 2 + 120, 190
    # a faint isometric floor grid, still, so only the box turns
    ctx = cv.ctx
    for i in range(-4, 5):
        for a, b in (((i * 60, -240), (i * 60, 240)), ((-240, i * 60), (240, i * 60))):
            ctx.move_to(*iso_point(a[0], 0, a[1], 0, cx, cy))
            ctx.line_to(*iso_point(b[0], 0, b[1], 0, cx, cy))
    ctx.set_source_rgba(*vb.rgba(demo.LINE))
    ctx.set_line_width(2)
    ctx.stroke()
    yaw = stepped_turns(demo.phase(n, 0.25, 2.95), steps=3)
    box = isometric_box(cv, cx, cy, size, yaw)
    cv.mark('box', *box)


CAPABILITY = Capability(
    id='isometric-rotation',
    name='Isometric rotation',
    family='shapes',
    group='Isometric',
    aliases=('isometric turntable', 'isometric spin', 'isometric orbit view'),
    definition='An object drawn in a flat isometric view turns about its upright axis in quarter steps, '
               'pausing after each so a different pair of sides faces the viewer every time.',
    phrasings=('turn the isometric box round so we see every side',
               'rotate the 3D-looking cube a quarter turn at a time',
               'spin the isometric icon in steps to show all its faces'),
    related=('turntable-rotation', 'isometric-assembly', 'isometric-view', 'globe-spin', 'character-rotate-in',
             'spin'),
    api=('videobuilder.capabilities.shapes.isometric_rotation.isometric_box',
         'videobuilder.capabilities.shapes.isometric_rotation.stepped_turns',
         'videobuilder.capabilities.shapes.isometric_rotation.iso_point'),
    demo=lambda: demo.film(draw),
)
