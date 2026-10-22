"""Rim light: a light behind the subject catches only its edge, so a dark
silhouette is outlined by a thin bright crescent on the side facing the
light, thickest where the edge turns toward it and gone on the far side."""
import math

import cairo

import videobuilder as vb
from videobuilder.canvas import rgba
from videobuilder.type import kit

from .. import _demo as demo
from ..schema import Technique


def rim_mask(cv, shape, angle, width):
    """Paint, in white, the part of the shape lying within `width` px of its
    edge as seen from a light in direction `angle` (radians, screen axes: 0 is
    to the right, -pi/2 straight up): the shape minus itself shifted `width`
    away from the light. `shape(ctx)` appends a closed path in frame coords."""
    c = cv.ctx
    dx, dy = math.cos(angle) * width, math.sin(angle) * width
    c.save()
    c.push_group()
    c.new_path()
    shape(c)
    c.set_source_rgba(1, 1, 1, 1)
    c.fill()
    c.set_operator(cairo.OPERATOR_DEST_OUT)
    c.translate(-dx, -dy)
    c.new_path()
    shape(c)
    c.fill()
    c.pop_group_to_source()
    c.paint()
    c.restore()


def draw_rim_light(cv, shape, box, angle, color='#ffd27a', fill='#23262f', width=5, glow=16, strength=1.0,
                   wash=0.22):
    """Draw a silhouette lit from behind: `shape(ctx)` (a closed path in frame
    coords, inside `box`) filled with `fill` (None leaves it unfilled), then a
    rim of `color` along the edge facing a light in direction `angle`
    (radians, screen axes: 0 right, -pi/2 up). The rim is a hard crescent
    `width` px at its thickest, a soft `wash` of light reaching three times
    as far into the shape, and a blurred halo of `glow` px spilling past the
    edge. `strength` 0..1 dims the whole rim (fade the light up or down).
    Returns `box`."""
    c = cv.ctx
    strength = vb.clamp01(strength)
    if fill is not None:
        c.save()
        c.new_path()
        shape(c)
        c.set_source_rgba(*rgba(fill))
        c.fill()
        c.restore()
    if strength <= 0 or width <= 0:
        return box

    def tinted(sub, w):
        sc = sub.ctx
        sc.save()
        sc.push_group()
        rim_mask(sub, shape, angle, w)
        sc.set_operator(cairo.OPERATOR_IN)
        sc.set_source_rgba(*rgba(color))
        sc.paint()
        sc.pop_group_to_source()
        sc.paint()
        sc.restore()

    if glow > 0:
        kit.blurred(cv, box, glow, lambda sub: tinted(sub, width * 1.6), alpha=0.75 * strength)
    if wash > 0:
        kit.blurred(cv, box, width * 1.5, lambda sub: tinted(sub, width * 3), alpha=wash * strength)
    with cv.layer(opacity=strength):
        tinted(cv, width)
    return box


CX, CY = demo.W / 2, demo.H / 2 + 20
HEAD = (CX, CY - 120, 92, 118)   # centre x, y and radii of the head
BASE = CY + 230                  # where the shoulders are cut off


def bust(ctx):
    """A head-and-shoulders silhouette as one closed outline."""
    hx, hy, rx, ry = HEAD
    neck = hy + ry * math.sin(math.radians(62))
    ctx.move_to(CX - 270, BASE)
    ctx.curve_to(CX - 270, BASE - 120, CX - 200, neck + 70, CX - 110, neck + 52)
    ctx.curve_to(CX - 62, neck + 42, CX - 46, neck + 30, CX - 44, neck)
    ctx.save()
    ctx.translate(hx, hy)
    ctx.scale(rx, ry)
    ctx.arc(0, 0, 1, math.radians(118), math.radians(62) + 2 * math.pi)
    ctx.restore()
    ctx.curve_to(CX + 46, neck + 30, CX + 62, neck + 42, CX + 110, neck + 52)
    ctx.curve_to(CX + 200, neck + 70, CX + 270, BASE - 120, CX + 270, BASE)
    ctx.close_path()


SWING = vb.ease.bezier(0.45, 0, 0.55, 1)


def draw(n, cv):
    # The light swings round behind the figure, from upper left over the top to upper right,
    # and the bright edge slides round the outline with it.
    a = math.radians(-160 + 140 * SWING(demo.phase(n, 0.3, 2.7)))
    box = vb.Box(CX - 280, HEAD[1] - HEAD[3] - 10, 560, BASE - (HEAD[1] - HEAD[3]) + 10)
    draw_rim_light(cv, bust, box, a, color='#ffcf6b', width=6, glow=18,
                   strength=0.25 + 0.75 * demo.phase(n, 0.0, 0.5))
    cv.mark('subject', *box)


TECHNIQUE = Technique(
    id='rim-light',
    name='Rim light',
    family='camera',
    group='Lighting & surface',
    aliases=('edge light', 'back light', 'backlight', 'kicker light', 'hair light'),
    definition='A dark subject is outlined by a thin bright edge on the side facing a light placed behind it, '
               'which lifts its shape clear of the background.',
    phrasings=('put a glowing edge of light around the silhouette',
               'light the figure from behind so just its outline shines',
               'give the shape a bright rim so it pops off the dark background'),
    related=('fresnel-edge-glow', 'shine-glint-sweep', 'spotlight-dim', 'gooch-shading', 'gradient-border-spin',
             'spotlight-hover'),
    api=('videobuilder.techniques.camera.rim_light.draw_rim_light',
         'videobuilder.techniques.camera.rim_light.rim_mask'),
    demo=lambda: demo.film(draw),
)
