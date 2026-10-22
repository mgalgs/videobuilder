"""Letter Morph: one letter's outline flows into another's -- every contour
of the first glyph slides point by point onto a contour of the second, and
a hole the other letter lacks shrinks shut (or opens up) as it goes."""
import math
from functools import lru_cache

import cairo
import gi

import videobuilder as vb

from ... import text
from .. import _demo as demo
from ..schema import Technique

gi.require_version('PangoCairo', '1.0')
from gi.repository import PangoCairo  # noqa: E402


@lru_cache(maxsize=256)
def glyph_contours(s, font):
    """`s`'s glyph outlines, flattened, as a tuple of closed point lists in
    px about the line's centre (its advance width by its line height)."""
    ctx = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1))
    content, _ = text._content(font)
    lh = text.line_height(font)
    ctx.move_to(-text.measure(s, font) / 2, -lh / 2 + (lh - content) / 2)
    PangoCairo.layout_path(ctx, text._layout(ctx, s, font))
    contours, cur = [], []
    for kind, pts in ctx.copy_path_flat():
        if kind == cairo.PATH_MOVE_TO:
            if len(cur) > 2:
                contours.append(tuple(cur))
            cur = [pts]
        elif kind == cairo.PATH_LINE_TO:
            cur.append(pts)
        elif kind == cairo.PATH_CLOSE_PATH:
            if len(cur) > 2:
                contours.append(tuple(cur))
            cur = []
    if len(cur) > 2:
        contours.append(tuple(cur))
    return tuple(contours)


def _area(pts):
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1])) / 2


def _centre(pts):
    return sum(x for x, _ in pts) / len(pts), sum(y for _, y in pts) / len(pts)


def _pair(a, b, n):
    """Match `a`'s contours to `b`'s -- outlines to outlines, holes to holes
    (told apart by winding against the largest), nearest centres first --
    as `(start, end)` pairs of `n`-point lists, start and end aligned so
    points travel the short way round. A contour left unmatched pairs with
    a single point at its own centre, so it grows out of or shrinks into
    nothing."""
    def split(contours):
        if not contours:
            return [], []
        sign = math.copysign(1, max((_area(list(c)) for c in contours), key=abs))
        outer = [list(c) for c in contours if _area(list(c)) * sign > 0]
        holes = [list(c) for c in contours if _area(list(c)) * sign <= 0]
        return outer, holes

    pairs = []
    for ca, cb in zip(split(a), split(b)):
        ca, cb = list(ca), list(cb)
        while ca and cb:
            i, j = min(((i, j) for i in range(len(ca)) for j in range(len(cb))),
                       key=lambda ij: math.dist(_centre(ca[ij[0]]), _centre(cb[ij[1]])))
            x, y = ca.pop(i), cb.pop(j)
            pairs.append((vb.paths.morph(x, y, 0, closed=True, n=n), vb.paths.morph(x, y, 1, closed=True, n=n)))
        for c in ca:
            pairs.append((vb.paths.resample(c, n, closed=True), [_centre(c)] * n))
        for c in cb:
            pairs.append(([_centre(c)] * n, vb.paths.resample(c, n, closed=True)))
    return pairs


@lru_cache(maxsize=64)
def _pairs(a, b, font, n):
    return _pair(glyph_contours(a, font), glyph_contours(b, font), n)


def letter_morph(a, b, font, p, n=160):
    """The outline of text `a` turning into text `b` at progress `p` (0 -> 1,
    clamped; ease it yourself), as a list of closed point lists about the
    centre of the line. Usually one letter to one letter, but any two
    strings work. `n`: points per contour."""
    p = vb.clamp01(p)
    return [[(x0 + (x1 - x0) * p, y0 + (y1 - y0) * p) for (x0, y0), (x1, y1) in zip(s, e)]
            for s, e in _pairs(a, b, font, n)]


def draw_letter_morph(cv, a, b, font, cx, cy, p, color, alpha=1.0, n=160):
    """Fill `letter_morph(a, b, font, p)` centred at (cx, cy) in `color`,
    holes cut out even-odd. Returns the Box of the drawn shape."""
    contours = [[(cx + x, cy + y) for x, y in c] for c in letter_morph(a, b, font, p, n)]
    ctx = cv.ctx
    ctx.new_path()
    for c in contours:
        ctx.move_to(*c[0])
        for pt in c[1:]:
            ctx.line_to(*pt)
        ctx.close_path()
    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    ctx.set_source_rgba(*vb.rgba(color, alpha))
    ctx.fill()
    ctx.set_fill_rule(cairo.FILL_RULE_WINDING)
    xs = [x for c in contours for x, _ in c]
    ys = [y for c in contours for _, y in c]
    return vb.Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


LETTERS = 'ABC'
MORPHS = ((0.35, 1.15), (1.75, 2.55))  # seconds each A -> B, B -> C runs


def draw(n, cv):
    f = demo.font(520, 800)
    i, p = 0, 0.0
    for k, (start, end) in enumerate(MORPHS):
        if n / demo.FPS >= start:
            i, p = k, vb.ease_in_out_quart(demo.phase(n, start, end))
    box = draw_letter_morph(cv, LETTERS[i], LETTERS[i + 1], f, demo.W / 2, demo.H / 2, p, demo.INK)
    cv.mark('letter', *box)


TECHNIQUE = Technique(
    id='letter-morph',
    name='Letter morph',
    family='typography',
    group='Morphing',
    aliases=('glyph morph', 'character shape morph', 'word morph', 'ligature morph'),
    definition="A letter's outline bends and slides continuously until it has become the shape "
               'of a different letter.',
    phrasings=('have the A melt into a B',
               'the letter reshapes itself into the next one',
               'morph one character into another instead of cutting'),
    related=('shape-morph', 'outline-to-fill', 'glyph-cycling', 'morphing-shape-ident',
             'per-character-fade-in', 'particle-morph'),
    api=('videobuilder.techniques.typography.letter_morph.draw_letter_morph',
         'videobuilder.techniques.typography.letter_morph.letter_morph',
         'videobuilder.techniques.typography.letter_morph.glyph_contours'),
    demo=lambda: demo.film(draw),
)
