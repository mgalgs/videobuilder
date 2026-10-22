"""Focus blur-out: everything in the shot except one region drifts out of
focus (and dims a little), so the region left sharp becomes the subject --
the explainer and broadcast way of saying "look here"."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ...type.kit import blurred


def _outside(cv, box, radius):
    """Clip `cv` to the whole frame minus the rounded `box`."""
    x, y, w, h = box
    r = max(0.0, min(radius, w / 2, h / 2))
    c = cv.ctx
    c.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    c.new_path()
    c.rectangle(0, 0, cv.width, cv.height)
    c.new_sub_path()
    c.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    c.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    c.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    c.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    c.close_path()
    c.clip()
    c.set_fill_rule(cairo.FILL_RULE_WINDING)


def focus_blur_out(cv, scene, focus, p, radius=22, dim=0.35, corner=16, color='#05060a', ring=None,
                   ring_width=3, background=None):
    """Draw `scene(cv)` with everything outside the rounded box `focus`
    (x, y, w, h) blurred by up to `radius` px and darkened by up to `dim`
    (0 -> 1) with `color`, at progress `p` (0 -> 1; run it back down to
    bring the frame into focus again). Inside `focus` the scene stays
    crisp. `ring`, a colour, outlines the focus box as it settles. Give the
    frame's `background` when `scene` leaves it unpainted, so the blur pulls
    in picture rather than dark at the frame's edges.

    In a film: `focus_blur_out(cv, lambda c: shot(c, f), target_box, vb.ease_out_cubic(t))`."""
    p = vb.clamp01(p)
    scene(cv)
    if p <= 0:
        return
    box = vb.Box.of(cv)
    r = radius * p
    pad = r * 2.5
    grow = 1 + 2 * pad / min(box.w, box.h)

    def paint(c):
        # an enlarged copy underneath, so the blur pulls in picture at the frame's edges
        with c.layer(dx=box.cx * (1 - grow), dy=box.cy * (1 - grow), scale=grow):
            if background is not None:
                c.fill(background)
            scene(c)
        with c.clip(box.x, box.y, box.w, box.h):
            if background is not None:
                c.fill(background)
            scene(c)
    cv.ctx.save()
    _outside(cv, focus, corner)
    blurred(cv, box, r, paint, alpha=min(1.0, p * 3))
    if dim > 0:
        cv.fill(color, alpha=dim * p)
    cv.ctx.restore()
    if ring is not None:
        cv.outline(*focus, ring, width=ring_width, radius=corner, alpha=p)


# ---- the demo: a small dashboard; the middle card stays sharp ----

CARDS = [(demo.W / 2 + dx, demo.H / 2 + dy, color)
         for dx, dy, color in ((-270, -50, '#3a3e4a'), (0, -50, demo.ACCENT), (270, -50, '#3a3e4a'),
                               (-270, 130, demo.TEAL), (0, 130, '#3a3e4a'), (270, 130, '#3a3e4a'))]
FOCUS = vb.Box(demo.W / 2 - 128, demo.H / 2 - 50 - 80, 256, 160)


def _board(cv):
    demo.word(cv, 'Weekly report', demo.W / 2, 64, size=40, weight=800)
    for cx, cy, color in CARDS:
        demo.card(cv, cx, cy, w=220, h=130, color=color)


def draw(n, cv):
    p = vb.ease_in_out_quart(demo.phase(n, 0.6, 1.7))
    focus_blur_out(cv, _board, FOCUS, p, radius=20, dim=0.4, corner=22, ring=demo.INK, ring_width=2,
                   background=demo.BG)
    cv.mark('focus', *FOCUS)


TECHNIQUE = Technique(
    id='focus-blur-out',
    name='Focus blur-out',
    family='broadcast',
    group='Annotation',
    aliases=('focus blur', 'background blur highlight', 'selective blur', 'blur to highlight'),
    definition='The rest of the picture goes soft and a little darker while one chosen area stays sharp, '
               'pulling the eye onto it.',
    phrasings=('blur everything except the chart we are talking about',
               'keep the one card crisp and let the rest of the screen go out of focus',
               'defocus the background to point at that part of the shot'),
    related=('depth-of-field', 'focus-breathing', 'rack-focus', 'gaussian-blur', 'focus-ring-draw',
             'character-blur-in'),
    api=('videobuilder.techniques.broadcast.focus_blur_out.focus_blur_out', 'videobuilder.type.kit.blurred'),
    demo=lambda: demo.film(draw),
)
