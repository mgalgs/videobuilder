"""Origami Fold: the outgoing scene is a sheet of paper. Its four corners fold
in to the middle, the diamond left folds in half, then in half again, and
the small folded packet shrinks away over the incoming scene."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

_EASE = vb.bezier(0.65, 0, 0.35, 1)


def _seg(p, start, end):
    return _EASE(vb.clamp01((p - start) / (end - start)))


def _fold_matrix(q, d, u, theta):
    """The affine map folding paper about the crease through `q` along `d`
    by `theta` (0 flat, pi folded right over): a point at `b` steps of `u`
    from the crease moves to `b * cos(theta)` steps, so seen from the front
    the flap swings across the crease. `u` need not be square to `d`, which
    lets a non-square sheet fold its corners exactly onto its centre."""
    wx, wy = -d[1], d[0]
    k = (math.cos(theta) - 1) / (d[0] * u[1] - d[1] * u[0])
    xx, xy = 1 + k * u[0] * wx, k * u[0] * wy
    yx, yy = k * u[1] * wx, 1 + k * u[1] * wy
    wq = wx * q[0] + wy * q[1]
    return cairo.Matrix(xx, yx, xy, yy, -k * u[0] * wq, -k * u[1] * wq)


def _path(c, pts):
    c.new_path()
    c.move_to(*pts[0])
    for pt in pts[1:]:
        c.line_to(*pt)
    c.close_path()


def _paint(c, sheet, scale):
    """Paint the offscreen `sheet` (device px at `scale`) in frame coordinates."""
    c.save()
    c.scale(1 / scale, 1 / scale)
    c.set_source_surface(sheet.surface, 0, 0)
    c.get_source().set_filter(cairo.FILTER_GOOD)
    c.paint()
    c.restore()


def _mask(c, sheet, scale, rgba):
    """Fill wherever `sheet` has paper with the colour `rgba`."""
    c.save()
    c.scale(1 / scale, 1 / scale)
    c.set_source_rgba(*rgba)
    c.mask_surface(sheet.surface, 0, 0)
    c.restore()


def _flap(c, sheet, scale, poly, crease, u, theta, back, tone):
    """The part of `sheet` inside `poly` folded by `theta` about `crease`
    (two points) towards `u`: its picture while it faces us, then the paper's
    `back` colour, shaded by how steeply it is tilted, plus `tone` extra shade
    so each finished facet reads apart from its neighbours."""
    (x0, y0), (x1, y1) = crease
    theta = min(theta, math.pi - 1e-3)
    if abs(math.cos(theta)) < 1e-3:
        return  # edge-on: no width to draw
    c.save()
    c.transform(_fold_matrix((x0, y0), (x1 - x0, y1 - y0), u, theta))
    _path(c, poly)
    c.clip()
    if math.cos(theta) > 0:
        _paint(c, sheet, scale)
        shade = 0.5 * (1 - math.cos(theta))
    else:
        _mask(c, sheet, scale, vb.canvas.rgba(back))
        shade = 0.45 * (1 + math.cos(theta)) + tone
    _mask(c, sheet, scale, (0, 0, 0, shade))
    c.restore()
    if theta > 0.05:  # the crease, only where there is paper under it
        c.push_group()
        c.move_to(x0, y0)
        c.line_to(x1, y1)
        c.set_source_rgba(0, 0, 0, 0.25 * min(1.0, theta))
        c.set_line_width(2)
        c.stroke()
        c.pop_group_to_source()
        c.save()
        c.scale(1 / scale, 1 / scale)
        c.mask_surface(sheet.surface, 0, 0)
        c.restore()


def _rest(c, sheet, scale, polys):
    """`sheet` with the regions in `polys` cut out: the part that stays put."""
    c.save()
    c.new_path()
    c.rectangle(-1, -1, 1e5, 1e5)
    for poly in polys:
        c.move_to(*poly[0])
        for pt in poly[1:]:
            c.line_to(*pt)
        c.close_path()
    c.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    c.clip()
    _paint(c, sheet, scale)
    c.restore()


def _blank(cv):
    return vb.Canvas(cv.width, cv.height, scale=cv.scale, format=cv.format)


def origami_fold(cv, a, b, p, back=demo.ACCENT):
    """Draw the fold at progress `p` (0 -> 1) over `b(cv)`: `a(cv)` is the
    sheet. Its four corners fold in to meet at the centre (showing the paper's
    `back` colour), the diamond folds top over bottom, the triangle folds left
    over right, and the packet shrinks and turns away.

    In a film, call it while two shots are live in an overlap, e.g.
    `origami_fold(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    W, H, s = cv.width, cv.height, cv.scale
    cx, cy = W / 2, H / 2
    t1 = _seg(p, 0.0, 0.4) * math.pi
    t2 = _seg(p, 0.36, 0.64) * math.pi
    t3 = _seg(p, 0.6, 0.84) * math.pi
    t4 = _seg(p, 0.78, 1.0)
    b(cv)

    sheet = _blank(cv)
    a(sheet)

    # 1. The corners fold in along the creases joining the edge midpoints.
    top, right, bottom, left = (cx, 0), (W, cy), (cx, H), (0, cy)
    corners = (((0, 0), (top, left), 0.0), ((W, 0), (top, right), 0.08),
               ((W, H), (bottom, right), 0.16), ((0, H), (bottom, left), 0.06))

    def stage1(c):
        _rest(c, sheet, s, [(k, e0, e1) for k, (e0, e1), _ in corners])
        for k, crease, tone in corners:
            _flap(c, sheet, s, (k, *crease), crease, (cx - k[0], cy - k[1]), t1, back, tone)

    # 2. The diamond folds top over bottom; 3. the triangle folds left over right.
    upper = ((0, 0), (W, 0), (W, cy), (0, cy))
    lefthalf = ((0, 0), (cx, 0), (cx, H), (0, H))

    def stage2(c, sheet):
        _rest(c, sheet, s, [upper])
        _flap(c, sheet, s, upper, (left, right), (0, H / 2), t2, back, 0.12)

    def stage3(c, sheet):
        _rest(c, sheet, s, [lefthalf])
        _flap(c, sheet, s, lefthalf, (top, bottom), (W / 2, 0), t3, back, 0.2)

    c = cv.ctx
    c.save()
    c.push_group()
    if t4 > 0:  # the packet drifts from where it lies to the centre, shrinking and turning
        px, py = W * 2 / 3, H * 2 / 3
        c.translate(px + (cx - px) * t4, py + (cy - py) * t4)
        c.rotate(-0.6 * t4)
        c.scale(1 - t4, 1 - t4)
        c.translate(-px, -py)
    if p >= 0.36:
        flat = _blank(cv)
        stage1(flat.ctx)
        if p >= 0.6:
            half = _blank(cv)
            stage2(half.ctx, flat)
            stage3(c, half)
        else:
            stage2(c, flat)
    else:
        stage1(c)
    paper = c.pop_group()
    base = paper.get_matrix()
    paper.set_matrix(cairo.Matrix(x0=-10, y0=-16).multiply(base))  # a hard drop shadow lifts the paper off `b`
    c.set_source_rgba(0, 0, 0, 0.3 * min(1.0, 6 * p))
    c.mask(paper)
    paper.set_matrix(base)
    c.set_source(paper)
    c.paint()
    c.restore()


CAPABILITY = Capability(
    id='origami-fold',
    name='Origami fold',
    family='transitions',
    group='Page and Fold',
    aliases=('paper fold', 'polygon fold', 'faceted fold'),
    definition='The outgoing picture creases like a sheet of paper, folding into flat angled facets '
               'again and again until the small folded piece leaves the next scene behind it.',
    phrasings=('fold the first shot up like paper to get to the next one',
               'make the frame fold itself away origami-style',
               'crease the picture into triangles and fold it off screen'),
    related=('paper-fold-reveal', 'accordion-fold-text', 'twist-deformer', 'corner-wipe',
             'cut-out-paper-animation', 'tessellation-triangle-flip'),
    api=('videobuilder.capabilities.transitions.origami_fold.origami_fold',),
    demo=lambda: demo.two_scenes(origami_fold, start=0.5, length=2.0),
)
