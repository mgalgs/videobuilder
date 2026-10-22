"""Fresnel edge glow: a rounded body facing the camera stays dark in the
middle and brightens towards its silhouette, where the surface turns away
from the eye, so it reads as glass, a force field or a hologram."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def fresnel(r, power=3.0, base=0.0):
    """Schlick's approximation of the Fresnel term at `r` (0 at the centre,
    1 at the silhouette) of a sphere seen head-on: `base` facing the eye,
    rising to 1 at grazing angles. Larger `power` hugs the edge tighter."""
    r = vb.clamp01(r)
    facing = math.sqrt(1 - r * r)                 # cos of the angle between normal and view
    return base + (1 - base) * (1 - facing) ** power


def fresnel_pattern(cx, cy, r, color, power=3.0, base=0.0, strength=1.0, steps=24):
    """A cairo radial gradient over the disc (cx, cy, r): `color` at an alpha
    following `fresnel` from centre to rim, times `strength`. Paint it over
    any round body to give it the edge glow."""
    g = cairo.RadialGradient(cx, cy, 0, cx, cy, r)
    red, green, blue, a = vb.rgba(color)
    for i in range(steps + 1):
        t = i / steps
        t = 1 - (1 - t) ** 2                       # more stops near the rim, where it changes fastest
        g.add_color_stop_rgba(t, red, green, blue, a * vb.clamp01(strength * fresnel(t, power, base)))
    return g


def fresnel_sphere(cv, cx, cy, r, glow='#7fe8ff', body='#0d1a24', power=3.0, base=0.04, strength=1.0,
                   halo=0.35, light=(-0.45, -0.5)):
    """Draw a sphere of radius `r` at (cx, cy) with a Fresnel edge glow in
    `glow`: a dim `body` with soft key light from `light` (an offset in
    radii), the glow climbing to full at the silhouette, and an outer
    `halo` (0 for none) bleeding a little past the edge. Animate `strength`
    to bring the glow up, `power` to widen or tighten it."""
    ctx = cv.ctx
    if halo > 0 and strength > 0:
        red, green, blue, a = vb.rgba(glow)
        g = cairo.RadialGradient(cx, cy, r * 0.9, cx, cy, r * 1.45)
        g.add_color_stop_rgba(0, red, green, blue, a * halo * strength)
        g.add_color_stop_rgba(0.35, red, green, blue, a * halo * strength * 0.35)
        g.add_color_stop_rgba(1, red, green, blue, 0)
        ctx.set_source(g)
        ctx.arc(cx, cy, r * 1.45, 0, 2 * math.pi)
        ctx.fill()
    ctx.save()
    ctx.arc(cx, cy, r, 0, 2 * math.pi)
    ctx.clip()
    ctx.set_source_rgba(*vb.rgba(body))
    ctx.paint()
    lx, ly = cx + light[0] * r, cy + light[1] * r
    key = cairo.RadialGradient(lx, ly, 0, lx, ly, r * 1.3)
    key.add_color_stop_rgba(0, 1, 1, 1, 0.10)
    key.add_color_stop_rgba(1, 1, 1, 1, 0)
    ctx.set_source(key)
    ctx.paint()
    if strength > 0:
        ctx.set_source(fresnel_pattern(cx, cy, r, glow, power, base, strength))
        ctx.paint()
    ctx.restore()
    cv.mark('sphere', cx - r, cy - r, 2 * r, 2 * r)


def draw(n, cv):
    t = n / demo.FPS
    up = 1 - (1 - demo.phase(n, 0.3, 1.4)) ** 3         # glow comes on
    power = 1.6 + 1.8 * demo.phase(n, 1.6, 2.7)         # then tightens onto the rim
    cx = demo.W / 2 + 20 * math.sin(2 * math.pi * t / demo.SECONDS)
    cy = demo.H / 2 + 8 * math.sin(4 * math.pi * t / demo.SECONDS)
    fresnel_sphere(cv, cx - 290, cy + 80, 55, glow=demo.TEAL, power=power, strength=up)
    fresnel_sphere(cv, cx + 280, cy - 70, 75, glow=demo.TEAL, power=power, strength=up)
    fresnel_sphere(cv, cx, cy, 150, glow=demo.TEAL, power=power, strength=up)


TECHNIQUE = Technique(
    id='fresnel-edge-glow',
    name='Fresnel edge glow',
    family='camera',
    group='Shader looks',
    aliases=('fresnel effect', 'fresnel rim', 'facing ratio glow', 'edge falloff glow', 'hologram rim'),
    definition='A round object stays dark where it faces you and lights up towards its outline, '
               'glowing brightest right at the edge as if light were grazing off its curved sides.',
    phrasings=('make the ball glow around its edges like glass or a force field',
               'a dark orb with a bright rim that fades in towards the middle',
               'give the shape that holographic edge light'),
    related=('rim-light', 'thin-film-iridescence', 'subsurface-scattering-glow', 'border-glow-follow',
             'glow-button', 'shine-glint-sweep'),
    api=('videobuilder.techniques.camera.fresnel_edge_glow.fresnel_sphere',
         'videobuilder.techniques.camera.fresnel_edge_glow.fresnel_pattern',
         'videobuilder.techniques.camera.fresnel_edge_glow.fresnel'),
    demo=lambda: demo.film(draw),
)
