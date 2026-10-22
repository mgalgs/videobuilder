"""Rack focus: the shot holds still while the plane of sharp focus slides from
a near subject to a far one, so the first goes soft as the second sharpens."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ...type.kit import blurred


def rack_focus(cv, planes, p, blur=26):
    """Draw `planes` at rack progress `p` (0 -> 1), back to front.

    `planes` is a sequence of `(depth, paint)` pairs, `paint(cv)` drawing one
    layer of the shot. Depth is measured along the focus pull: a plane at
    depth 0 is sharp when `p` is 0, one at depth 1 is sharp when `p` is 1, and
    every plane is blurred by `blur` px per unit of distance from the focal
    depth `p`. List them far to near so nearer layers paint over farther ones.

    In a film, pass an eased progress, e.g.
    `rack_focus(cv, [(1, draw_far), (0, draw_near)], vb.ease_in_out_quart(shot.f / pull_frames))`."""
    box = vb.Box.of(cv)
    for depth, paint in planes:
        blurred(cv, box, blur * abs(depth - p), paint)


def _far(cv):
    cx, cy = demo.W * 0.68, demo.H * 0.38
    cv.shadow(cx - 120, cy + 140, 240, 24, radius=12, blur=18, color=(0, 0, 0, 0.5))
    demo.card(cv, cx, cy, w=300, h=190, color=demo.TEAL)


def _near(cv):
    cx, cy = demo.W * 0.3, demo.H * 0.64
    cv.shadow(cx - 110, cy + 112, 220, 30, radius=15, blur=22, color=(0, 0, 0, 0.55))
    demo.dot(cv, cx, cy, r=110)


def draw(n, cv):
    p = vb.ease_in_out_quart(demo.phase(n, 0.6, 2.2))
    rack_focus(cv, [(1, _far), (0, _near)], p)


TECHNIQUE = Technique(
    id='rack-focus',
    name='Rack focus',
    family='camera',
    group='Depth',
    aliases=('focus pull', 'pull focus', 'focus shift', 'rack'),
    definition='With the frame held still, the sharp zone glides from one subject to another at a '
               'different distance, blurring the first as the second comes clear.',
    phrasings=('move the focus from the thing up front to the thing behind it',
               'blur the foreground and bring the background into focus',
               'pull focus between two objects in the shot'),
    related=('focus-blur-out', 'focus-breathing', 'character-blur-in', 'whip-pan', 'focus-ring-draw',
             'push-in'),
    api=('videobuilder.techniques.camera.rack_focus.rack_focus', 'videobuilder.type.kit.blurred'),
    demo=lambda: demo.film(draw),
)
