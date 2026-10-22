"""Shape Boolean Merge: two separate shapes slide into each other and fuse
into one silhouette -- a single fill and a single outline, the seams where
they overlapped gone -- as a vector union (or subtract, intersect, exclude)
would leave them."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

OPS = ('union', 'subtract', 'intersect', 'exclude')


def circle_points(cx, cy, r, n=96):
    """A circle as a closed point list, for `boolean_shape`."""
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def rounded_rect_points(cx, cy, w, h, radius=0, n=12):
    """A rounded rectangle centred at (cx, cy) as a closed point list, `n`
    points per corner, for `boolean_shape`."""
    r = max(0.0, min(radius, w / 2, h / 2))
    corners = ((cx + w / 2 - r, cy - h / 2 + r, -math.pi / 2), (cx + w / 2 - r, cy + h / 2 - r, 0.0),
               (cx - w / 2 + r, cy + h / 2 - r, math.pi / 2), (cx - w / 2 + r, cy - h / 2 + r, math.pi))
    pts = []
    for ox, oy, a0 in corners:
        for i in range(n + 1):
            a = a0 + (math.pi / 2) * i / n
            pts.append((ox + r * math.cos(a), oy + r * math.sin(a)))
    return pts


def _trace(ctx, points):
    ctx.new_sub_path()
    ctx.move_to(*points[0])
    for p in points[1:]:
        ctx.line_to(*p)
    ctx.close_path()


def boolean_shape(cv, a, b, op='union', color=demo.ACCENT, alpha=1.0, outline=None, width=0):
    """Fill the boolean `op` of two closed point lists `a` and `b` as one
    shape: 'union' (both, merged), 'subtract' (a with b cut away),
    'intersect' (only where they overlap) or 'exclude' (either but not
    both). The result is composited once, so overlaps leave no seam and
    `alpha` does not double up. `outline` strokes the result's outer edge,
    `width` px, only for 'union' (where it is exact: inner edges vanish).

    Animate a merge by moving `a` and `b` into each other frame by frame;
    pair with a two-colour draw that cross-fades into this (see the demo)."""
    if op not in OPS:
        raise ValueError(f'boolean_shape: op must be one of {", ".join(OPS)}, not {op!r}')
    c = cv.ctx
    c.save()
    c.push_group()
    if op == 'intersect':
        _trace(c, a)
        c.clip()
        _trace(c, b)
        c.set_source_rgba(*vb.rgba(color))
        c.fill()
    else:
        if op == 'union' and outline and width > 0:
            # Stroke both at double width, then fill both over it: only the
            # outer half of each stroke survives, along the merged edge.
            _trace(c, a)
            _trace(c, b)
            c.set_source_rgba(*vb.rgba(outline))
            c.set_line_width(2 * width)
            c.set_line_join(cairo.LINE_JOIN_ROUND)
            c.stroke()
        c.set_fill_rule(cairo.FILL_RULE_WINDING)
        c.set_source_rgba(*vb.rgba(color))
        _trace(c, a)
        c.fill()
        if op != 'union':
            c.set_operator(cairo.OPERATOR_DEST_OUT if op == 'subtract' else cairo.OPERATOR_XOR)
        _trace(c, b)
        c.fill()
    c.pop_group_to_source()
    c.paint_with_alpha(alpha)
    c.restore()


def _separate(cv, a, b, ca, cb, alpha=1.0):
    """The two shapes before the merge: each its own colour and outline,
    the overlap tinted so both edges read."""
    c = cv.ctx
    with cv.layer(opacity=alpha):
        for pts, col in ((a, ca), (b, cb)):
            _trace(c, pts)
            c.set_source_rgba(*vb.rgba(col, 0.55))
            c.fill()
        boolean_shape(cv, a, b, 'intersect', demo.INK, alpha=0.35)
        for pts, col in ((a, ca), (b, cb)):
            _trace(c, pts)
            c.set_source_rgba(*vb.rgba(col))
            c.set_line_width(3)
            c.stroke()


def draw(n, cv):
    t = n / demo.FPS
    slide = vb.ease_out_quint(demo.phase(n, 0.15, 1.2))
    merge = vb.ease_in_out_quart(demo.phase(n, 1.45, 1.95))
    cx, cy = demo.W / 2, demo.H / 2
    gap = 300 * (1 - slide)
    a = circle_points(cx - 70 - gap, cy - 20, 120)
    b = rounded_rect_points(cx + 85 + gap, cy - 20, 200, 200, radius=28)
    if merge < 1:
        _separate(cv, a, b, demo.ACCENT, demo.TEAL, alpha=1 - merge)
    if merge > 0:
        # A small settle as the two become one.
        pop = 1 + 0.05 * math.sin(math.pi * demo.phase(n, 1.75, 2.35))
        with cv.layer(dx=cx * (1 - pop), dy=(cy - 20) * (1 - pop), scale=pop):
            boolean_shape(cv, a, b, 'union', demo.ACCENT, alpha=merge, outline=demo.INK, width=3)
    label = 'A + B' if t < 1.7 else 'A ∪ B'
    demo.word(cv, label, cx, demo.H - 60, size=30, color=demo.MUTED, weight=700)
    cv.mark('shape', cx - 190 - gap, cy - 140, 375 + 2 * gap, 240)


TECHNIQUE = Technique(
    id='shape-boolean-merge',
    name='Shape boolean merge',
    family='shapes',
    group='Shape morphing',
    aliases=('boolean union', 'shape union', 'merge shapes', 'pathfinder merge', 'shape builder'),
    definition='Two separate shapes move into each other and fuse into one solid form, '
               'the lines where they overlapped disappearing so a single outline remains.',
    phrasings=('the circle and the square slide together and become one shape',
               'combine the two shapes into a single blob with one outline',
               'merge the pieces like a union in a vector app, but animated'),
    related=('morph-cut', 'circle-packing', 'shape-morph', 'polygon-subdivision', 'shape-fill-sweep',
             'geometric-loop'),
    api=('videobuilder.techniques.shapes.shape_boolean_merge.boolean_shape',
         'videobuilder.techniques.shapes.shape_boolean_merge.circle_points',
         'videobuilder.techniques.shapes.shape_boolean_merge.rounded_rect_points'),
    demo=lambda: demo.film(draw),
)
