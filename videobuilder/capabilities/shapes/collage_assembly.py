"""Collage assembly: paper cut-outs -- a sheet, a scrap of colour, a photo, a
strip of tape -- arrive one after another, each sliding in lifted off the
page and pressing down onto the pile until the collage is complete."""
import math
import random
from dataclasses import dataclass

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


@dataclass(frozen=True)
class Piece:
    """One cut-out. `points`: its outline about its own centre; `x, y`: where
    that centre rests; `angle`: its resting tilt in degrees; `color`: its
    fill; `came_from`: the (dx, dy) offset it slides in from; `spin`: extra
    degrees it turns through on the way; `paint`: an optional `paint(cv)`
    drawing its face over the fill, in the piece's own coordinates (clipped
    to the outline); `grain`: a paper-grain seed, or None for a flat fill."""
    points: tuple
    x: float
    y: float
    angle: float = 0.0
    color: str = '#e9e6df'
    came_from: tuple = (0.0, -700.0)
    spin: float = 0.0
    paint: object = None
    grain: object = 0


def cut(w, h, ragged=0.0, seed=0):
    """A w x h rectangle outline about (0, 0), its corners nudged by up to
    `ragged` px so it reads as hand-cut paper rather than a UI box."""
    r = random.Random(seed)
    j = lambda: r.uniform(-ragged, ragged)  # noqa: E731
    return ((-w / 2 + j(), -h / 2 + j()), (w / 2 + j(), -h / 2 + j()),
            (w / 2 + j(), h / 2 + j()), (-w / 2 + j(), h / 2 + j()))


def disc(r, sides=48):
    """A circle outline of radius `r` about (0, 0), as points."""
    return tuple((r * math.cos(2 * math.pi * i / sides), r * math.sin(2 * math.pi * i / sides))
                 for i in range(sides))


def arrival(p, i, count, overlap=0.35):
    """Piece `i` of `count`'s own progress 0 -> 1 at overall progress `p`:
    the pieces come one by one, each starting before the last has quite
    landed (`overlap` of a slot)."""
    slot = 1 / (count - (count - 1) * overlap) if count > 1 else 1.0
    start = i * slot * (1 - overlap)
    return vb.clamp01((p - start) / slot)


def draw_piece(cv, piece, t, lift=0.08, shadow=(0, 0, 0, 0.45)):
    """Draw `piece` at its own progress `t` (0 -> 1): off at `came_from`,
    raised by `lift` and casting a long soft shadow, it slides in, then
    presses flat onto the page with a tight shadow. Nothing is drawn at
    t <= 0."""
    if t <= 0:
        return
    move = vb.ease_out_quint(vb.clamp01(t / 0.8))
    press = vb.clamp01((t - 0.65) / 0.35)     # the last third: settle down onto the paper
    height = 1 - press * press * (3 - 2 * press)
    dx, dy = piece.came_from
    x, y = piece.x + dx * (1 - move), piece.y + dy * (1 - move)
    angle = math.radians(piece.angle + piece.spin * (1 - move))
    s = 1 + lift * height
    c, si = math.cos(angle), math.sin(angle)
    pts = [(x + s * (px * c - py * si), y + s * (px * si + py * c)) for px, py in piece.points]
    off, blur = 4 + 26 * height, 6 + 30 * height
    cv.shape_shadow(pts, dx=off * 0.4, dy=off, blur=blur, color=shadow)
    ctx = cv.ctx
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(angle)
    ctx.scale(s, s)
    ctx.move_to(*piece.points[0])
    for px, py in piece.points[1:]:
        ctx.line_to(px, py)
    ctx.close_path()
    ctx.clip_preserve()
    ctx.set_source_rgba(*vb.rgba(piece.color))
    ctx.fill()
    if piece.paint:
        piece.paint(cv)
    if piece.grain is not None:
        ctx.set_source(vb.paper_grain(cv.width, cv.height, seed=piece.grain))
        ctx.set_operator(cairo.OPERATOR_SOFT_LIGHT)
        ctx.paint_with_alpha(0.45)
        ctx.set_operator(cairo.OPERATOR_OVER)
    ctx.restore()


def draw_collage(cv, pieces, p, overlap=0.35, **kw):
    """Assemble `pieces` (a sequence of `Piece`, bottom first) at overall
    progress `p` (0 -> 1): each arrives in turn and lands on the ones before
    it. `kw` goes to `draw_piece`."""
    for i, piece in enumerate(pieces):
        draw_piece(cv, piece, arrival(p, i, len(pieces), overlap), **kw)


def _ruled(cv):
    for k in range(-5, 7):
        cv.rect(-150, k * 22 - 6, 260 if k % 4 else 160, 6, '#b9b6ae', radius=3)


def _snapshot(cv):
    cv.rect(-150, -100, 300, 200, '#2a3350')
    cv.ctx.move_to(-150, 40)
    cv.ctx.curve_to(-60, -20, 20, 70, 150, 0)
    cv.ctx.line_to(150, 100)
    cv.ctx.line_to(-150, 100)
    cv.ctx.close_path()
    cv.ctx.set_source_rgba(*vb.rgba(demo.TEAL))
    cv.ctx.fill()
    demo.dot(cv, 80, -45, 26, color='#f2c14e')


def _photo_frame(cv):
    cv.rect(-150, -100, 300, 200, '#2a3350')
    cv.ctx.save()
    cv.ctx.translate(-12, -12)
    cv.ctx.scale(0.88, 0.88)
    _snapshot(cv)
    cv.ctx.restore()


def _stripes(cv):
    for k in range(-8, 9):
        cv.line(k * 18 - 80, 120, k * 18 + 80, -120, '#ffffff', width=5, alpha=0.35)


CX, CY = demo.W / 2, demo.H / 2

PIECES = (
    Piece(cut(360, 280, 6, seed=1), CX - 40, CY - 10, -6, '#e9e6df', came_from=(-1100, 0),
          spin=-14, paint=_ruled, grain=1),
    Piece(disc(110), CX + 150, CY - 120, 0, '#8a8cf0', came_from=(700, -600), grain=2),
    Piece(cut(240, 90, 10, seed=3), CX - 150, CY + 120, -8, '#f2b632', came_from=(-500, 700),
          spin=20, grain=3),
    Piece(cut(330, 230, 2, seed=4), CX + 40, CY + 20, 4, '#f6f4ef', came_from=(0, -900),
          spin=12, paint=_photo_frame, grain=4),
    Piece(cut(96, 190, 6, seed=5), CX + 210, CY + 110, 14, '#6f72e6', came_from=(900, 300),
          spin=30, paint=_stripes, grain=5),
    Piece(cut(150, 44, 4, seed=6), CX - 130, CY - 150, -22, '#d8d4e8', came_from=(-300, -700),
          spin=-40, grain=6),
)


def draw(n, cv):
    draw_collage(cv, PIECES, demo.phase(n, 0.2, 2.5))
    cv.mark('collage', CX - 260, CY - 230, 520, 460)


TECHNIQUE = Technique(
    id='collage-assembly',
    name='Collage assembly',
    family='shapes',
    group='Cut-out & paper',
    aliases=('cut-and-paste collage', 'scrapbook layering', 'layered cut-outs'),
    definition='Paper cut-outs of shapes, colour and pictures slide in one after another and press down '
               'on top of each other until they make a finished collage.',
    phrasings=('build the picture up out of paper scraps one at a time',
               'pieces fly in and stack up like a scrapbook page',
               'make it look like a cut-and-paste collage putting itself together'),
    related=('shape-assemble-from-fragments', 'shape-stacking-drop', 'crumple', 'particle-text-formation',
             'voxel-build', 'isometric-assembly'),
    api=('videobuilder.techniques.shapes.collage_assembly.draw_collage',
         'videobuilder.techniques.shapes.collage_assembly.Piece',
         'videobuilder.techniques.shapes.collage_assembly.draw_piece',
         'videobuilder.techniques.shapes.collage_assembly.arrival',
         'videobuilder.techniques.shapes.collage_assembly.cut'),
    demo=lambda: demo.film(draw),
)
