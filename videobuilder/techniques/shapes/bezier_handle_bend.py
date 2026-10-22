"""Bezier handle bend: a stroke between two fixed anchors is bent by moving
the two control handles of its cubic Bezier, the line flexing from straight
into an arc or an S as the handles swing out."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def bend_handles(a, b, bend_a, bend_b, reach=1 / 3):
    """The two control points of a cubic from anchor `a` to anchor `b`. Each
    handle starts `reach` of the way along the chord from its own anchor and
    is pushed sideways (perpendicular to the chord, to the left going a -> b)
    by `bend_a` / `bend_b` px. Both 0 is a straight line; equal signs bow it
    into an arc, opposite signs bend it into an S."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    d = math.hypot(dx, dy) or 1.0
    nx, ny = dy / d, -dx / d
    c1 = (a[0] + dx * reach + nx * bend_a, a[1] + dy * reach + ny * bend_a)
    c2 = (b[0] - dx * reach + nx * bend_b, b[1] - dy * reach + ny * bend_b)
    return c1, c2


def cubic_points(a, c1, c2, b, steps=64):
    """The cubic Bezier a -> b with controls c1, c2 as `steps + 1` points, for
    `vb.paths` (reveal, morph, draw)."""
    out = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        w0, w1, w2, w3 = u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t
        out.append((w0 * a[0] + w1 * c1[0] + w2 * c2[0] + w3 * b[0],
                    w0 * a[1] + w1 * c1[1] + w2 * c2[1] + w3 * b[1]))
    return out


def draw_bend(cv, a, b, bend_a, bend_b, color, width=8, handles=True, handle_color=None, alpha=1.0):
    """Draw the stroke a -> b bent by `bend_a` / `bend_b` (see `bend_handles`).
    `handles` also draws the editor-style rig: a thin tangent line from each
    anchor to its handle, square anchors and round handle knobs. Returns the
    two control points."""
    c1, c2 = bend_handles(a, b, bend_a, bend_b)
    vb.paths.draw(cv, cubic_points(a, c1, c2, b), color, width=width, alpha=alpha)
    if handles:
        hc = handle_color or color
        k = max(4.0, width * 0.9)
        for anchor, ctrl in ((a, c1), (b, c2)):
            cv.line(*anchor, *ctrl, hc, width=2, alpha=0.7 * alpha)
            cv.sector(*ctrl, k, 0, 2 * math.pi, hc, alpha=alpha)
            cv.rect(anchor[0] - k, anchor[1] - k, 2 * k, 2 * k, demo.INK, alpha=alpha)
    return c1, c2


def draw(n, cv):
    a, b = (360, demo.H / 2), (demo.W - 360, demo.H / 2)
    # straight -> bowed arc -> S-curve -> straight, each move eased with a little overshoot
    keys = ((0.3, 0, 0), (1.0, -230, -230), (1.7, -230, 230), (2.5, 0, 0))
    bend_a = bend_b = 0.0
    for (t0, a0, b0), (t1, a1, b1) in zip(keys, keys[1:]):
        p = vb.ease_out_back(demo.phase(n, t0, t1 - 0.1))
        if n / demo.FPS >= t0:
            bend_a, bend_b = a0 + (a1 - a0) * p, b0 + (b1 - b0) * p
    c1, c2 = draw_bend(cv, a, b, bend_a, bend_b, demo.ACCENT, width=10, handle_color=demo.TEAL)
    xs, ys = (a[0], b[0], c1[0], c2[0]), (a[1], b[1], c1[1], c2[1])
    cv.mark('curve', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys) or 1)


TECHNIQUE = Technique(
    id='bezier-handle-bend',
    name='Bezier handle bend',
    family='shapes',
    group='Lines & strokes',
    aliases=('bezier bend', 'control handle bend', 'tangent handle animation', 'curve handle drag'),
    definition='A line pinned at both ends flexes into smooth arcs and S-shapes as the control handles '
               'of its curve swing out and back.',
    phrasings=('bend the line by pulling its curve handles',
               'make a straight stroke curve into an S and back',
               'animate the bezier handles so the path flexes'),
    related=('arc-bend-morph', 'bend-deformer', 'pendulum-swing', 'custom-cubic-bezier-easing',
             'dragon-curve', 'twist-deformer'),
    api=('videobuilder.techniques.shapes.bezier_handle_bend.draw_bend',
         'videobuilder.techniques.shapes.bezier_handle_bend.bend_handles',
         'videobuilder.techniques.shapes.bezier_handle_bend.cubic_points'),
    demo=lambda: demo.film(draw),
)
