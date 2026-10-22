"""Long Shadow Extension: a flat shape drags a solid, hard-edged shadow out
along a diagonal, and the shadow's length is what animates -- it reaches out,
then pulls back."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ...canvas import rgba
from ...looks import kit as looks


def circle_points(cx, cy, r, steps=72):
    """A circle as a closed point list, for `draw_long_shadow`."""
    return [(cx + r * math.cos(2 * math.pi * i / steps), cy + r * math.sin(2 * math.pi * i / steps))
            for i in range(steps)]


def _area(pts):
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1])) / 2


def _subpath(ctx, pts):
    if _area(pts) < 0:      # one winding for every piece, so the nonzero fill is their union
        pts = pts[::-1]
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()


def long_shadow_pieces(points, length, angle=45):
    """The polygons whose union is the long shadow of the closed polygon
    `points` cast `length` px along `angle` degrees (0 = right, 90 = down):
    the shape, the shape moved to the shadow's far end, and the quad each
    edge sweeps between them. Works for any simple polygon, convex or not."""
    pts = [tuple(p) for p in points]
    dx, dy = length * math.cos(math.radians(angle)), length * math.sin(math.radians(angle))
    far = [(x + dx, y + dy) for x, y in pts]
    quads = [[a, b, (b[0] + dx, b[1] + dy), (a[0] + dx, a[1] + dy)] for a, b in zip(pts, pts[1:] + pts[:1])]
    return [pts, far] + [q for q in quads if abs(_area(q)) > 1e-6]


def draw_long_shadow(cv, points, length, color, angle=45, alpha=1.0):
    """Draw the hard-edged long shadow of the closed polygon `points`,
    `length` px along `angle` degrees, in `color`. Draw it before the shape
    itself; animate `length` (0 -> long -> shorter) to extend or retract it.
    Clip with `cv.clip` to keep it inside a tile, as flat icons do."""
    if length <= 0 or len(points) < 3:
        return
    c = cv.ctx
    c.save()
    c.new_path()
    for piece in long_shadow_pieces(points, length, angle):
        _subpath(c, piece)
    c.set_fill_rule(0)  # cairo.FILL_RULE_WINDING
    c.set_source_rgba(*rgba(color, alpha))
    c.fill()
    c.restore()


def shade(color, toward, k):
    """`color` mixed `k` (0 -> 1) of the way to `toward`: a shadow tone that
    keeps a hint of the shape's own hue."""
    a, b = rgba(color), rgba(toward)
    return tuple(round(255 * (x + (y - x) * k)) for x, y in zip(a[:3], b[:3]))


def _square(cx, cy, s):
    return [(cx - s, cy - s), (cx + s, cy - s), (cx + s, cy + s), (cx - s, cy + s)]


def _triangle(cx, cy, s):
    return [(cx, cy - s * 1.1), (cx + s * 1.05, cy + s * 0.75), (cx - s * 1.05, cy + s * 0.75)]


def draw(n, cv):
    out = vb.ease_out_expo(demo.phase(n, 0.3, 1.5))        # reach out
    back = vb.ease_in_out_quart(demo.phase(n, 1.9, 2.6))   # pull back part way
    length = 230 * out - 110 * back
    y = demo.H / 2 - 70
    shapes = ((circle_points(demo.W / 2 - 290, y, 52), demo.ACCENT),
              (_square(demo.W / 2 - 40, y, 47), demo.TEAL),
              (_triangle(demo.W / 2 + 210, y + 6, 53), demo.INK))
    for pts, color in shapes:
        draw_long_shadow(cv, pts, length, shade(color, demo.BG, 0.72))
    for pts, color in shapes:
        looks.fill(cv, pts, color)
    cv.mark('shapes', demo.W / 2 - 342, y - 58, 608, 110)


TECHNIQUE = Technique(
    id='long-shadow-extension',
    name='Long shadow extension',
    family='shapes',
    group='Depth & shadows',
    aliases=('long shadow', 'flat long shadow', 'shadow stretch'),
    definition='A flat shape trails a solid, sharp-edged shadow off at a diagonal, '
               'and the shadow reaches further out and then draws back in.',
    phrasings=('give the icon one of those long flat-design shadows that grows out',
               'the shadow stretches away diagonally from the shape and then shrinks back',
               'a hard diagonal shadow that slides out behind the logo'),
    related=('long-shadow-growth', 'drop-shadow-lift', 'shadow-play', 'bend-deformer', 'light-painting',
             'extrusion'),
    api=('videobuilder.techniques.shapes.long_shadow_extension.draw_long_shadow',
         'videobuilder.techniques.shapes.long_shadow_extension.long_shadow_pieces',
         'videobuilder.techniques.shapes.long_shadow_extension.circle_points'),
    demo=lambda: demo.film(draw),
)
