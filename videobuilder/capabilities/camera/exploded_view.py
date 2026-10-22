"""Exploded view: an assembled object in 3D separates along one axis, each
layer sliding away from its neighbours, so the gaps show every part and how
the parts stack and fit back together."""
import math

import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ..schema import Capability
from ..shapes.isometric_rotation import iso_point


def explode_offsets(p, levels, gap, anchor=0.0, stagger=0.12, ease=vb.ease_in_out_quart):
    """How far each of `levels` stacked layers has moved along the explode
    axis at progress `p` (0: assembled, 1: fully exploded). Layer `i` ends
    `(i - anchor) * gap` from where it sat, so layer `anchor` holds still
    and the others spread out either side of it; each starts `stagger` of
    the way after the layer nearer the anchor, so the stack peels apart
    from the anchor outwards."""
    far = max(abs(i - anchor) for i in range(levels)) or 1
    out = []
    for i in range(levels):
        delay = stagger * abs(i - anchor) / far
        local = vb.clamp01((p - delay) / (1 - stagger)) if stagger < 1 else vb.clamp01(p)
        out.append((i - anchor) * gap * ease(local))
    return out


def _slab(cv, at, x, y, z, w, d, h, color):
    """An axis-aligned box with its bottom-back-left corner at (x, y, z),
    `w` along x, `h` up, `d` along z; `at` projects a world point. Only the
    top and the two faces towards the viewer are drawn."""
    ctx = cv.ctx

    def face(pts, shade):
        ctx.move_to(*at(*pts[0]))
        for q in pts[1:]:
            ctx.line_to(*at(*q))
        ctx.close_path()
        ctx.set_source_rgba(*vb.rgba(shade))
        ctx.fill()

    x1, y1, z1 = x + w, y + h, z + d
    face([(x1, y, z), (x1, y, z1), (x1, y1, z1), (x1, y1, z)], kit.mix(color, '#000000', 0.38))
    face([(x, y, z1), (x1, y, z1), (x1, y1, z1), (x, y1, z1)], kit.mix(color, '#000000', 0.18))
    face([(x, y1, z), (x1, y1, z), (x1, y1, z1), (x, y1, z1)], kit.mix(color, '#ffffff', 0.12))


def exploded_view(cv, cx, cy, parts, p, gap=90, anchor=None, yaw=0.0, stagger=0.12, ease=vb.ease_in_out_quart,
                  guides=True, guide_color=demo.MUTED, shadow=True):
    """Draw `parts` in isometric projection about screen point (cx, cy),
    exploded along the vertical axis by progress `p` (0 -> 1).

    Each part is `(level, x, y, z, w, d, h, color)`: a box in world pixels,
    y up, centred on the origin, at its assembled position; `level` is the
    layer it belongs to (parts sharing a level travel together, e.g. a chip
    on its board). Levels spread `gap` pixels apart about `anchor` (default:
    the middle level) via `explode_offsets`. Thin `guides` run along the
    axis through the bottom layer's corners, so the shared alignment reads
    in the gaps; `shadow` drops a soft floor shadow under the whole stack.
    Returns the screen Box the parts cover."""
    levels = max(part[0] for part in parts) + 1
    anchor = (levels - 1) / 2 if anchor is None else anchor
    lift = explode_offsets(p, levels, gap, anchor, stagger, ease)

    def at(x, y, z):
        return iso_point(x, y, z, yaw, cx, cy)

    lo = min(part[2] for part in parts) + min(lift)
    hi = max(part[2] + part[6] + lift[part[0]] for part in parts)
    if shadow:
        base = [b for b in parts if b[0] == 0]
        hw = max(max(abs(b[1]), abs(b[1] + b[4])) for b in base)
        hd = max(max(abs(b[3]), abs(b[3] + b[5])) for b in base)
        floor = lo - gap * 0.8
        pts = [at(x, floor, z) for x, z in ((-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd))]
        cv.shape_shadow(pts, blur=gap * 0.6, color=(0, 0, 0, 0.55))
    if guides:
        ctx = cv.ctx
        corner = [b for b in parts if b[0] == 0][0]
        _, x, _, z, w, d, _, _ = corner
        ctx.set_dash([6, 8])
        for gx, gz in ((x, z), (x + w, z), (x + w, z + d), (x, z + d)):
            ctx.move_to(*at(gx, lo, gz))
            ctx.line_to(*at(gx, hi + gap * 0.4, gz))
        ctx.set_source_rgba(*vb.rgba(guide_color, 0.45 * vb.clamp01(p * 3)))
        ctx.set_line_width(2)
        ctx.stroke()
        ctx.set_dash([])
    order = sorted(parts, key=lambda b: (b[2] + lift[b[0]], b[1] + b[3]))
    xs, ys = [], []
    for level, x, y, z, w, d, h, color in order:
        y += lift[level]
        _slab(cv, at, x, y, z, w, d, h, color)
        for px, py, pz in ((x, y, z), (x + w, y + h, z + d), (x + w, y, z), (x, y + h, z + d)):
            sx, sy = at(px, py, pz)
            xs.append(sx)
            ys.append(sy)
    return vb.Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


SHELL, BOARD, CELL, CHIP, DARK, SCREW = '#6c74d8', '#3f8f84', '#d9d6cc', '#f2b33d', '#22242b', '#c9a34a'

# A small gadget: base shell, battery, circuit board with parts, lid with a
# screen, and four screws, bottom to top.
GADGET = [
    (0, -170, 0, -120, 340, 240, 46, SHELL),
    (1, -140, 0, -95, 280, 190, 18, CELL),
    (2, -150, 0, -105, 300, 210, 10, BOARD),
    (2, -40, 10, -40, 90, 70, 22, CHIP),
    (2, 70, 10, 20, 50, 34, 18, DARK),
    (2, -120, 10, 40, 40, 30, 12, DARK),
    (3, -170, 0, -120, 340, 240, 30, SHELL),
    (3, -90, 30, -60, 160, 90, 3, DARK),
] + [(4, sx - 9, 0, sz - 9, 18, 18, 22, SCREW) for sx in (-145, 145) for sz in (-95, 95)]

STACK_Y = {0: 0, 1: 46, 2: 64, 3: 96, 4: 126}  # where each level sits when assembled


def _demo_parts(k=0.42):
    return [(level, x * k, (y + STACK_Y[level]) * k, z * k, w * k, d * k, h * k, color)
            for level, x, y, z, w, d, h, color in GADGET]


def draw(n, cv):
    p = demo.phase(n, 0.45, 2.1)
    yaw = math.radians(-8 + 10 * demo.phase(n, 0, 3.0))
    box = exploded_view(cv, demo.W / 2, demo.H / 2 + 45, _demo_parts(), p, gap=46, yaw=yaw)
    cv.mark('assembly', *box)


CAPABILITY = Capability(
    id='exploded-view',
    name='Exploded view',
    family='camera',
    group='3D motion',
    aliases=('explode diagram', 'assembly explode', 'exploded layer stack', 'layer explode',
             'isometric layers'),
    definition='A built-up 3D object pulls apart along one axis, its layers spreading out with gaps between them '
               'so each part and where it fits can be seen.',
    phrasings=('take the device apart in the air so we see each layer',
               'pull the stack apart vertically to show what is inside',
               'separate every piece of the product like an assembly diagram'),
    related=('isometric-assembly', 'shape-assemble-from-fragments', 'depth-slicing', 'shatter', 'shape-burst',
             'type-explosion'),
    api=('videobuilder.capabilities.camera.exploded_view.exploded_view',
         'videobuilder.capabilities.camera.exploded_view.explode_offsets'),
    demo=lambda: demo.film(draw),
)
