"""Text-to-shape morph: a word's glyph outlines bend and flow into one solid
shape (a heart, a circle, a logo mark), letters setting off a beat apart.

The outlines come from Pango (`PangoCairo.layout_path`), flattened once and
cached; each outer contour travels onto the shape's outline with
`vb.paths.morph`, and each counter (the hole in an O or an A) shrinks away to
the shape's centre, so the word fills in to one clean silhouette."""
import math
from functools import lru_cache

import cairo
from gi.repository import PangoCairo

import videobuilder as vb
from videobuilder import text as vbtext

from .. import _demo as demo
from ..schema import Capability


@lru_cache(maxsize=64)
def glyph_contours(line, font):
    """`line`'s glyph contours as a tuple of `(index, points)`, px about the
    line's centre: `index` is the character each contour belongs to, so
    letters can be staggered."""
    ctx = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1))
    w, h = vbtext.block_size([line], font)
    content, _ = vbtext._content(font)
    edges = [vbtext.measure(line[:i + 1], font) - w / 2 for i in range(len(line))]
    ctx.move_to(-w / 2, -h / 2 + (vbtext.line_height(font) - content) / 2)
    PangoCairo.layout_path(ctx, vbtext._layout(ctx, line, font))
    contours, cur = [], []

    def close():
        if len(cur) > 2:
            cx = sum(x for x, _ in cur) / len(cur)
            contours.append((min(sum(1 for e in edges if e < cx), len(line) - 1), tuple(cur)))

    for kind, pts in ctx.copy_path_flat():
        if kind == cairo.PATH_MOVE_TO:
            close()
            cur = [pts]
        elif kind == cairo.PATH_LINE_TO:
            cur.append(pts)
        elif kind == cairo.PATH_CLOSE_PATH:
            close()
            cur = []
    close()
    return tuple(contours)


def _area(points):
    return 0.5 * sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(points, points[1:] + points[:1]))


def text_to_shape(line, font, shape, p, stagger=0.35, n=160):
    """The polygons of `line` morphing into `shape` at progress `p` (0 -> 1),
    both about (0, 0). `shape` is a closed point list in px about its own
    centre. Outer contours travel onto `shape`; counters (holes) shrink to its
    centre. Letter i starts `stagger * i / (len - 1)` of the way in and every
    letter lands at 1, each eased in-out (quartic). Fill the result with the nonzero
    rule (`vb.paths`-style polygons; see `draw_text_to_shape`)."""
    contours = glyph_contours(line, font)
    if not contours:
        return []
    outer = _area(list(max(contours, key=lambda c: abs(_area(list(c[1]))))[1])) >= 0
    shape = list(shape)
    cx = sum(x for x, _ in shape) / len(shape)
    cy = sum(y for _, y in shape) / len(shape)
    last = max(len(line) - 1, 1)
    out = []
    for i, pts in contours:
        start = stagger * i / last
        t = vb.ease_in_out_quart(vb.clamp01((p - start) / (1 - start)))
        pts = list(pts)
        if (_area(pts) >= 0) == outer:
            out.append(vb.paths.morph(pts, shape, t, closed=True, n=n))
        else:  # a counter: close up onto the shape's centre
            ra = vb.paths.resample(pts, n // 2, closed=True)
            out.append([(x + (cx - x) * t, y + (cy - y) * t) for x, y in ra])
    return out


def draw_text_to_shape(cv, line, font, cx, cy, shape, p, color, to_color=None, alpha=1.0, **kw):
    """Draw `line` morphing into `shape` at progress `p`, centred at (cx, cy),
    filled `color` (blending to `to_color` across the morph when given). `kw`
    goes to `text_to_shape`. Returns the Box of the polygons."""
    polys = text_to_shape(line, font, shape, p, **kw)
    if not polys:
        return vb.Box(cx, cy, 0, 0)
    rgba = vb.canvas.rgba(color, alpha)
    if to_color:
        k = vb.ease_in_out_quart(vb.clamp01(p))
        rgba = tuple(a + (b - a) * k for a, b in zip(rgba, vb.canvas.rgba(to_color, alpha)))
    c = cv.ctx
    c.save()
    c.new_path()
    c.set_fill_rule(cairo.FILL_RULE_WINDING)
    for poly in polys:
        c.move_to(cx + poly[0][0], cy + poly[0][1])
        for x, y in poly[1:]:
            c.line_to(cx + x, cy + y)
        c.close_path()
    c.set_source_rgba(*rgba)
    c.fill()
    c.restore()
    xs = [x for poly in polys for x, _ in poly]
    ys = [y for poly in polys for _, y in poly]
    return vb.Box(cx + min(xs), cy + min(ys), max(xs) - min(xs), max(ys) - min(ys))


def heart(size, n=240):
    """A heart outline `size` px wide, about its own centre: a closed point list."""
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        x = 16 * math.sin(a) ** 3
        y = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
        pts.append((x * size / 32, -(y + 2.5) * size / 32))
    return pts


SHAPE = heart(420)


def draw(n, cv):
    p = demo.phase(n, 0.6, 2.2)
    box = draw_text_to_shape(cv, 'LOVE', demo.font(220, 900), demo.W / 2, demo.H / 2, SHAPE, p,
                             demo.INK, to_color=demo.ACCENT)
    cv.mark('morph', *box)


CAPABILITY = Capability(
    id='text-to-shape-morph',
    name='Text-to-shape morph',
    family='typography',
    group='Morphing',
    aliases=('type to shape morph', 'word to icon morph', 'letter morph', 'text shape tween'),
    definition='The outlines of a word stretch and flow, letter by letter, until together they '
               'become a single solid shape or icon.',
    phrasings=('the word melts and reshapes itself into a heart',
               'turn the title letters into the logo shape',
               'letters morph together into an icon'),
    related=('shape-morph', 'chart-type-morph', 'symbol-to-letter-decode', 'morphing-shape-ident',
             'blob-to-icon-morph', 'icon-state-morph'),
    api=('videobuilder.capabilities.typography.text_to_shape_morph.draw_text_to_shape',
         'videobuilder.capabilities.typography.text_to_shape_morph.text_to_shape',
         'videobuilder.capabilities.typography.text_to_shape_morph.glyph_contours'),
    demo=lambda: demo.film(draw),
)
