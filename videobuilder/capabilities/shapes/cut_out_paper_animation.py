"""Cut-out paper animation: a figure made of flat paper pieces, each with a
thin cast shadow, hinged at its joints and moved in held steps, as if
re-posed by hand between exposures on a table."""
import math
import random

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def held(n, every=2, seed=None, boil=0.0):
    """Stop-motion timing for frame `n`: `(frame, dx, dy, turn)`. `frame` is
    `n` held for `every` frames (on twos by default), so sample all motion at
    it. With a `seed`, `dx, dy` (px, up to `boil`) and `turn` (radians) are a
    small hand-placement wobble, re-drawn once per held frame, to add to a
    piece's own placement; otherwise they are 0."""
    f = n - n % every
    if seed is None or not boil:
        return f, 0.0, 0.0, 0.0
    r = random.Random(f'{seed}:{f}')
    return f, r.uniform(-boil, boil), r.uniform(-boil, boil), math.radians(r.uniform(-0.8, 0.8) * boil)


def paper_piece(cv, points, color, x=0.0, y=0.0, angle=0.0, lift=6.0, grain=0.45, seed=0,
                edge='#ffffff', shadow=(0, 0, 0, 0.5), sx=1.0, sy=1.0):
    """One cut paper shape: the closed outline `points` (local px, its pivot at
    0, 0) filled flat in `color`, placed with its pivot at (x, y) and turned
    `angle` radians about it and stretched `sx`, `sy` (a negative `sy` folds
    a wing over its hinge), in the current transform. Under it a soft shadow
    offset `lift` px down and a little right, the gap between the paper and
    the table; on it a clipped paper grain (`grain`, 0 for none, `seed` picks
    the texture) and a faint `edge` where the cut catches the light.

    Pieces nest like a rig: draw a parent, then, inside `cv.ctx.save()` and a
    translate/rotate to its joint, its children. The shadow mask is cached per
    outline, so a piece that only moves and turns blurs once."""
    c = cv.ctx
    c.save()
    c.translate(x, y)
    if angle:
        c.rotate(angle)
    if (sx, sy) != (1.0, 1.0):
        c.scale(sx, sy)
    if lift:
        cv.shape_shadow(points, dx=lift * 0.45, dy=lift, blur=max(2.0, lift * 1.4), color=shadow)
    c.new_path()
    c.move_to(*points[0])
    for p in points[1:]:
        c.line_to(*p)
    c.close_path()
    c.set_source_rgba(*vb.rgba(color))
    c.fill_preserve()
    c.save()
    c.clip_preserve()
    if grain:
        c.set_source(vb.paper_grain(cv.width, cv.height, seed=seed))
        c.set_operator(cairo.OPERATOR_SOFT_LIGHT)
        c.paint_with_alpha(grain)
        c.set_operator(cairo.OPERATOR_OVER)
    c.set_source_rgba(*vb.rgba(edge, 0.35))
    c.set_line_width(3)
    c.stroke_preserve()
    c.restore()
    c.new_path()
    c.restore()


# ---- the demo: a paper bird flapping across the table, on twos ----

BODY = [(-95, -8), (-45, -48), (35, -52), (88, -22), (82, 26), (22, 48), (-62, 36)]
TAIL = [(8, -14), (-105, -40), (-92, 4), (-110, 30), (8, 18)]
HEAD = [(-30, 10), (-28, -40), (2, -66), (40, -60), (58, -28), (40, 8), (6, 22)]
BEAK = [(50, -42), (96, -30), (50, -16)]
WING = [(-34, 6), (-70, -128), (-34, -158), (6, -150), (34, 6)]
FLAP = ((1.0, -0.3), (0.55, -0.1), (-0.15, 0.1), (-0.6, 0.2), (-0.15, 0.1), (0.55, -0.1))  # (fold, turn) poses, held four frames each

BLUE, LILAC, GOLD, PAPER = '#6f7ae0', '#5560c4', '#f2b51e', '#f1ede4'


def ellipse(rx, ry, k=24):
    return [(rx * math.cos(2 * math.pi * i / k), ry * math.sin(2 * math.pi * i / k)) for i in range(k)]


SPOT = ellipse(120, 18)


def bird(cv, x, y, wing, tilt, lift):
    c = cv.ctx
    c.save()
    c.translate(x, y)
    c.rotate(tilt)
    fold, turn = wing
    paper_piece(cv, WING, LILAC, -4, -30, turn - 0.3, lift * 0.6, seed=4, sy=fold * 0.85)  # far wing
    paper_piece(cv, TAIL, LILAC, -80, 0, -0.08 + fold * 0.1, lift, seed=1)
    paper_piece(cv, BODY, BLUE, lift=lift, seed=2)
    c.save()
    c.translate(70, -30)
    c.rotate(fold * -0.06)
    paper_piece(cv, BEAK, GOLD, lift=lift * 0.7, seed=5)
    paper_piece(cv, HEAD, GOLD, lift=lift, seed=3)
    demo.dot(cv, 22, -36, r=6, color=demo.BG)
    c.restore()
    paper_piece(cv, WING, PAPER, -10, -22, turn, lift * 1.3, seed=6, sy=fold)  # near wing, lifted most
    c.restore()


def draw(n, cv):
    cv.fill(demo.BG)
    cv.ctx.set_source(vb.paper_grain(cv.width, cv.height, seed=9))
    cv.ctx.set_operator(cairo.OPERATOR_SOFT_LIGHT)
    cv.ctx.paint_with_alpha(0.25)
    cv.ctx.set_operator(cairo.OPERATOR_OVER)
    f, jx, jy, jr = held(n, 2, seed='bird', boil=2.0)
    t = f / demo.FPS
    x = demo.W * 0.27 + (demo.W * 0.5) * t / demo.SECONDS
    hop = abs(math.sin(math.pi * t * 1.6))
    y = demo.H * 0.5 - 60 * hop
    wing = FLAP[(f // 4) % len(FLAP)]
    floor = demo.H * 0.78
    cv.shape_shadow([(x + px, floor + py) for px, py in SPOT], blur=30, color=(0, 0, 0, 0.55 - 0.2 * hop))
    bird(cv, x + jx, y + jy, wing, jr - 0.06 + 0.1 * math.cos(math.pi * t * 1.6), 8 + 4 * hop)
    cv.mark('bird', x - 210, y - 200, 330, 270)


TECHNIQUE = Technique(
    id='cut-out-paper-animation',
    name='Cut-out paper animation',
    family='shapes',
    group='Cut-out & paper',
    aliases=('paper cutout', 'cut paper', 'paper collage', 'layered paper', 'silhouette cut animation'),
    definition='A figure built from flat, hinged pieces of coloured paper, each casting a thin shadow, '
               'is re-posed in small jerky steps like a hand-moved model shot frame by frame.',
    phrasings=('animate it like paper cut-outs being moved around on a table',
               'make the character out of construction paper pieces that move in stop-motion',
               'a handmade, papercraft look where flat shapes jerk from pose to pose'),
    related=('crumple', 'morph-cut', 'cut-on-action', 'smash-cut', 'origami-fold', 'strobe-cut'),
    api=('videobuilder.techniques.shapes.cut_out_paper_animation.paper_piece',
         'videobuilder.techniques.shapes.cut_out_paper_animation.held'),
    demo=lambda: demo.film(draw),
)
