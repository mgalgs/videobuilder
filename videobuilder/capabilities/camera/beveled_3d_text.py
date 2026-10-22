"""Beveled 3D text: the word is a solid block with rounded front edges, lit
from one side, so the bevels catch a highlight on the edges facing the light
and fall into shade on the far ones; as the word swings round, the side and
the light on the bevels shift with it."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _shade(color, k):
    """`color` mixed towards black (k > 0) or white (k < 0) by |k|, as (r, g, b)."""
    r, g, b, _ = vb.rgba(color)
    t = 0.0 if k > 0 else 1.0
    k = abs(k)
    return tuple(round((c + (t - c) * k) * 255) for c in (r, g, b))


def _band(cv, text, font, x, y, ox, oy, color, alpha):
    """Paint the part of the glyphs at (x, y) that the same glyphs shifted by
    (ox, oy) don't cover: a thin rim along the edges facing away from the
    shift, in `color` at `alpha`."""
    ctx = cv.ctx
    ctx.push_group()
    vb.text.draw(cv, [text], font, x, y, color)
    ctx.set_operator(cairo.OPERATOR_DEST_OUT)
    vb.text.draw(cv, [text], font, x + ox, y + oy, '#000000')
    ctx.set_operator(cairo.OPERATOR_OVER)
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(alpha)


def draw_beveled_text(cv, text, font, cx, cy, color, light=-120.0, bevel=None, depth=None, yaw=0.0,
                      tilt=0.25, side_shade=0.55, highlight=0.85, shadow=0.6, steps=6, ground=True):
    """Draw `text` centred on (cx, cy) as a solid lit block with rounded
    bevelled front edges. `color` is the material; `light` is the screen
    direction the light comes from, in degrees (0 right, -90 straight up), so
    the bevels facing it brighten by up to `highlight` and the far ones darken
    by up to `shadow`. `bevel` is the bevel width and `depth` the block's
    thickness in px (defaults scale with the font). `yaw` (radians, about
    +-0.6) turns the block about its vertical axis -- foreshortening the face
    and showing the side on the far edge -- and `tilt` (radians) looks down
    onto its top. Each bevel is built from `steps` rims, bright at the edge
    and fading inward, so it reads as rounded rather than chamfered.
    `ground` adds a soft contact shadow under the block. Returns the Box of
    the face on screen (before the turn)."""
    size = font.size
    bevel = size * 0.05 if bevel is None else bevel
    depth = size * 0.22 if depth is None else depth
    w, h = vb.text.block_size([text], font)
    x, y = -w / 2, -h / 2
    ctx = cv.ctx
    sy, cyaw = math.sin(yaw), math.cos(yaw)
    # the depth runs away from the camera: sideways as it turns, down as we look over it
    dx, dy = -sy * depth, math.sin(tilt) * depth * 0.6 + abs(sy) * depth * 0.15

    if ground:
        gw, gy = w * cyaw * 0.55, cy + h * 0.62 + depth * 0.5
        g = cairo.RadialGradient(0, 0, 0, 0, 0, 1)
        g.add_color_stop_rgba(0, 0, 0, 0, 0.55)
        g.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.save()
        ctx.translate(cx + dx / 2, gy)
        ctx.scale(gw, h * 0.09)
        ctx.arc(0, 0, 1, 0, 2 * math.pi)
        ctx.set_source(g)
        ctx.fill()
        ctx.restore()

    ctx.save()
    ctx.translate(cx, cy)
    # a turned block: the face narrows and its far side drops, like a card swung in perspective
    ctx.transform(cairo.Matrix(cyaw, sy * 0.18, 0, 1, 0, 0))

    # the solid side: stacked copies, darkening towards the back
    slices = max(1, math.ceil(depth))
    for i in range(slices, 0, -1):
        t = i / slices
        vb.text.draw(cv, [text], font, x + dx * t, y + dy * t, _shade(color, side_shade * (0.55 + 0.45 * t)))

    # the face, a touch lighter at the top like a soft key light from above
    ctx.push_group()
    vb.text.draw(cv, [text], font, x, y, '#ffffff')
    mask = ctx.pop_group()
    grad = cairo.LinearGradient(0, y, 0, y + h)
    grad.add_color_stop_rgb(0, *(c / 255 for c in _shade(color, -0.15)))
    grad.add_color_stop_rgb(1, *(c / 255 for c in _shade(color, 0.12)))
    ctx.set_source(grad)
    ctx.mask(mask)

    # the bevels: rims whose edges face the light brighten, the far ones darken
    lx, ly = math.cos(math.radians(light)), math.sin(math.radians(light))
    for k in range(steps, 0, -1):
        r = bevel * k / steps
        a = 1.0 / steps * 1.6
        _band(cv, text, font, x, y, -lx * r, -ly * r, _shade(color, -1.0), highlight * a)
        _band(cv, text, font, x, y, lx * r, ly * r, _shade(color, 1.0), shadow * a)
    # a crisp specular line right on the lit edge
    _band(cv, text, font, x, y, -lx * bevel * 0.2, -ly * bevel * 0.2, '#ffffff', highlight)
    ctx.restore()
    return vb.Box(cx - w * cyaw / 2, cy - h / 2, w * cyaw, h)


def draw(n, cv):
    f = demo.font(190, 900)
    swing = vb.ease_in_out_quart(demo.phase(n, 0.2, 2.7))
    yaw = -0.55 * (1 - swing) + 0.12 * math.sin(math.pi * swing)
    light = -150 + 70 * swing          # the key light slides from upper left towards the top
    box = draw_beveled_text(cv, 'SOLID', f, demo.W / 2, demo.H / 2 - 20, '#d9dce2', light=light, yaw=yaw,
                            tilt=0.3)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='beveled-3d-text',
    name='Beveled 3D text',
    family='camera',
    group='3D motion',
    aliases=('lit 3D text', 'solid 3D text', 'bevelled type', '3D title'),
    definition='Lettering built as a thick solid with softly rounded front edges, lit so the bevels '
               'facing the light gleam and the rest fall into shade as the word turns.',
    phrasings=('make the title a chunky 3D block with rounded lit edges',
               'the word should look like a solid object catching the light as it swings round',
               'give the text a real bevel and depth, like a carved logo turning in space'),
    related=('text-on-a-path', 'dot-matrix-text', 'solid-drawing', 'three-d-word-cube', 'arc-bend-morph',
             'extrusion-depth-reveal'),
    api=('videobuilder.capabilities.camera.beveled_3d_text.draw_beveled_text',),
    demo=lambda: demo.film(draw),
)
