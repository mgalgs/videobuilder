"""Subsurface Scattering Glow: a translucent body lit from behind, so light
soaks through its thin edge on the lit side and spreads a little way inside
before fading, like a hand held up to a lamp."""
import math

import cairo

import videobuilder as vb
from videobuilder.canvas import rgba
from videobuilder.layout import Box
from videobuilder.type import kit

from .. import _demo as demo
from ..schema import Capability


def _ellipse(ctx, cx, cy, rx, ry, tilt=0.0):
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(tilt)
    ctx.scale(rx, ry)
    ctx.new_path()
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()


def draw_scatter_glow(cv, cx, cy, rx, ry, light, color, glow=None, strength=1.0, depth=0.16, tilt=0.0):
    """Draw a translucent ellipse centred at (cx, cy) with radii `rx`, `ry`
    (turned `tilt` radians), lit from behind by a light in direction `light`
    (radians, screen angle from the centre: 0 = right, pi/2 = below). The
    body is `color` darkened; the rim facing the light glows `glow` (default
    `color` brightened) in a crescent that is sharp at the edge and soaks
    `depth` of the radius inward before fading, with a faint halo bleeding
    out past the edge. `strength` (0 -> 1) scales the light, so a light
    swinging out from behind the body can fade it. Returns the body's Box."""
    strength = vb.clamp01(strength)
    glow = glow or tuple(255 * min(1.0, c * 1.6 + 0.15) for c in rgba(color)[:3])
    r = max(rx, ry)
    box = Box(cx - r, cy - r, 2 * r, 2 * r)
    lx, ly = math.cos(light), math.sin(light)
    ctx = cv.ctx

    def crescent(sub, inset):
        # The body, less a copy of itself pushed away from the light: what is left is the lit rim.
        c = sub.ctx
        c.save()
        c.push_group()
        _ellipse(c, cx, cy, rx, ry, tilt)
        c.set_source_rgba(*rgba(glow))
        c.fill()
        _ellipse(c, cx - lx * r * inset, cy - ly * r * inset, rx, ry, tilt)
        c.set_operator(cairo.OPERATOR_CLEAR)
        c.fill()
        c.pop_group_to_source()
        c.paint()
        c.restore()

    if strength > 0:  # the light that leaks out past the rim
        kit.blurred(cv, box, r * 0.18, lambda sub: crescent(sub, depth * 0.5), alpha=0.35 * strength)

    base = tuple(255 * c * 0.22 for c in rgba(color)[:3])
    _ellipse(ctx, cx, cy, rx, ry, tilt)
    ctx.set_source_rgba(*rgba(base))
    ctx.fill()

    ctx.save()
    _ellipse(ctx, cx, cy, rx, ry, tilt)
    ctx.clip()
    # A faint transmitted wash across the body, brightest on the lit side.
    g = cairo.LinearGradient(cx + lx * r, cy + ly * r, cx - lx * r, cy - ly * r)
    cr, cg, cb, _ = rgba(color)
    g.add_color_stop_rgba(0, cr, cg, cb, 0.35 * strength)
    g.add_color_stop_rgba(0.6, cr, cg, cb, 0)
    ctx.set_source(g)
    ctx.paint()
    if strength > 0:
        kit.blurred(cv, box, r * depth * 0.6, lambda sub: crescent(sub, depth), alpha=0.9 * strength)
        kit.blurred(cv, box, r * 0.02, lambda sub: crescent(sub, 0.04), alpha=strength)
    ctx.restore()
    return box


def light_point(cv, x, y, r=10, color='#ffffff', halo=120, alpha=1.0):
    """A small bright point light at (x, y) with a soft halo `halo` px wide."""
    cr, cg, cb, _ = rgba(color)
    for rad, a in ((halo, 0.12), (r * 2.2, 0.6), (r, 1.0)):
        g = cairo.RadialGradient(x, y, 0, x, y, rad)
        g.add_color_stop_rgba(0, cr, cg, cb, a * alpha)
        g.add_color_stop_rgba(1, cr, cg, cb, 0)
        cv.ctx.set_source(g)
        cv.ctx.arc(x, y, rad, 0, 2 * math.pi)
        cv.ctx.fill()


AMBER = '#d9862b'
GLOW = '#ffc46b'
SWING = vb.ease.bezier(0.45, 0, 0.55, 1)  # a gentle in-out, so the light drifts rather than darts


def draw(n, cv):
    t = demo.phase(n, 0.0, demo.SECONDS)
    cx, cy, rx, ry = demo.W / 2, demo.H / 2, 135, 185
    a = -0.15 + SWING(t) * 2.6  # the light swings behind, from the right round under to the left
    lx, ly = cx + math.cos(a) * (rx + 45), cy + math.sin(a) * (ry + 20) * 0.8
    light_point(cv, lx, ly, r=6, halo=110)
    box = draw_scatter_glow(cv, cx, cy, rx, ry, a, AMBER, glow=GLOW, tilt=0.18)
    cv.mark('body', *box)


CAPABILITY = Capability(
    id='subsurface-scattering-glow',
    name='Subsurface scattering glow',
    family='camera',
    group='Lighting & surface',
    aliases=('SSS', 'subsurface scattering', 'translucent glow', 'skin glow', 'backlit translucency'),
    definition='A light behind a semi-transparent object shines through its thinnest edge, which glows warmly '
               'and fades softly inward, as if the material held the light inside it.',
    phrasings=('make the shape look waxy and lit from behind so its edge glows',
               'light coming through the edge of the object like through an ear or a grape',
               'a soft inner glow around the rim as a light moves behind it'),
    related=('fresnel-edge-glow', 'outline-pulse-glow', 'heat-haze', 'shine-glint-sweep', 'glow-button',
             'matcap-shading'),
    api=('videobuilder.capabilities.camera.subsurface_scattering_glow.draw_scatter_glow',
         'videobuilder.capabilities.camera.subsurface_scattering_glow.light_point'),
    demo=lambda: demo.film(draw),
)
