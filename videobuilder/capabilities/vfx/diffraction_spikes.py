"""Diffraction Spikes: a bright point of light throws thin straight rays out
from its core, evenly spaced round it, the way a camera's aperture blades
turn a star or a street lamp into a star shape. The rays grow and shrink
with the light's brightness."""
import math
import random

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def spike_count(blades):
    """How many rays an aperture of `blades` straight blades makes: an even
    count gives one ray per blade, an odd count twice as many (each blade's
    ray and its opposite don't overlap)."""
    return blades if blades % 2 == 0 else 2 * blades


def diffraction_spikes(cv, x, y, brightness=1.0, length=300, spikes=6, rotation=0.0, color='#ffffff',
                       width=None, core=None, glow=None):
    """Draw one star-filtered point light centred on (x, y), added as light
    over what is already drawn. `brightness` (0 -> 1+) scales everything:
    ray length grows with it, so a light swelling from 0 sprouts its rays.
    `length` is the full ray length at brightness 1, `spikes` the ray count
    (`spike_count(blades)` for a given aperture), `rotation` turns the star in
    radians (−π/2 points the first ray straight up). Each ray tapers from
    `width` px at the core to a point and fades along its length; `core` is
    the hot centre's radius and `glow` the soft halo's, both defaulting to a
    share of `length`. Nothing is drawn at `brightness` <= 0."""
    if brightness <= 0:
        return
    b = brightness
    reach = length * b
    width = width if width is not None else max(1.5, length * 0.012)
    core = core if core is not None else max(1.5, length * 0.02)
    glow = glow if glow is not None else length * 0.22
    r, g, bl, _ = vb.rgba(color)
    a = min(1.0, b)
    c = cv.ctx
    c.save()
    c.set_operator(cairo.OPERATOR_ADD)
    # soft halo
    halo = cairo.RadialGradient(x, y, 0, x, y, glow * (0.4 + 0.6 * b))
    halo.add_color_stop_rgba(0, r, g, bl, 0.55 * a)
    halo.add_color_stop_rgba(0.35, r, g, bl, 0.18 * a)
    halo.add_color_stop_rgba(1, r, g, bl, 0)
    c.set_source(halo)
    c.arc(x, y, glow * (0.4 + 0.6 * b), 0, 2 * math.pi)
    c.fill()
    # rays: thin wedges, bright at the core, fading out to the tip
    w = width * (0.5 + 0.5 * min(1.0, b))
    for i in range(spikes):
        ang = rotation + 2 * math.pi * i / spikes
        ux, uy = math.cos(ang), math.sin(ang)
        tx, ty = x + ux * reach, y + uy * reach
        grad = cairo.LinearGradient(x, y, tx, ty)
        grad.add_color_stop_rgba(0, r, g, bl, a)
        grad.add_color_stop_rgba(0.25, r, g, bl, 0.55 * a)
        grad.add_color_stop_rgba(1, r, g, bl, 0)
        c.set_source(grad)
        c.move_to(x - uy * w, y + ux * w)
        c.line_to(tx, ty)
        c.line_to(x + uy * w, y - ux * w)
        c.close_path()
        c.fill()
    # hot core
    hot = cairo.RadialGradient(x, y, 0, x, y, core * 2.5)
    hot.add_color_stop_rgba(0, 1, 1, 1, a)
    hot.add_color_stop_rgba(0.4, r, g, bl, 0.8 * a)
    hot.add_color_stop_rgba(1, r, g, bl, 0)
    c.set_source(hot)
    c.arc(x, y, core * 2.5, 0, 2 * math.pi)
    c.fill()
    c.restore()


_FIELD = [(random.Random(7 + i).uniform(60, demo.W - 60), random.Random(70 + i).uniform(60, demo.H - 60),
           random.Random(700 + i).uniform(0.15, 0.45), random.Random(7000 + i).uniform(0, 2 * math.pi))
          for i in range(40)]
_LIGHTS = ((demo.W * 0.22, demo.H * 0.3, 0.0, 150), (demo.W * 0.8, demo.H * 0.72, 1.1, 120),
           (demo.W * 0.76, demo.H * 0.22, 1.9, 90))


def draw(n, cv):
    t = n / demo.FPS
    # faint background stars, no spikes
    for sx, sy, s, ph in _FIELD:
        demo.dot(cv, sx, sy, r=1.6 + 1.6 * s, color='#c8cee0', alpha=s * (0.75 + 0.25 * math.sin(3 * t + ph)))
    # a few smaller lights twinkle, their rays flickering
    for lx, ly, ph, ln in _LIGHTS:
        tw = 0.45 + 0.35 * math.sin(2 * math.pi * (t / 1.5) + ph * 2)
        diffraction_spikes(cv, lx, ly, tw, length=ln, spikes=4, rotation=math.pi / 4, color='#cfd8ff')
    # the main light swells, flares its six rays wide, then settles back
    cx, cy = demo.W / 2, demo.H / 2
    swell = vb.ease_in_out_quart(demo.phase(n, 0.2, 1.4)) - 0.55 * vb.ease_in_out_quart(demo.phase(n, 1.8, 2.9))
    diffraction_spikes(cv, cx, cy, 0.15 + 0.95 * swell, length=420, spikes=6, rotation=-math.pi / 2 + 0.15 * t,
                       color='#e4ebff')
    cv.mark('star', cx - 420, cy - 420, 840, 840)


CAPABILITY = Capability(
    id='diffraction-spikes',
    name='Diffraction spikes',
    family='vfx',
    group='Lens effects',
    aliases=('starburst flare', 'star filter', 'aperture spikes', 'star glint'),
    definition='A bright point of light shoots thin straight rays out from its centre at even angles, '
               'turning it into a sharp star shape that grows and shrinks with its brightness.',
    phrasings=('make the light glint into a star with little rays',
               'give the bright spots that cross-shaped sparkle like a camera lens does',
               'the star should flare out with long thin points'),
    related=('lens-flare', 'starfield', 'shape-burst', 'scatter-plot-point-appear', 'meteor-shower',
             'electric-arc'),
    api=('videobuilder.capabilities.vfx.diffraction_spikes.diffraction_spikes',
         'videobuilder.capabilities.vfx.diffraction_spikes.spike_count'),
    demo=lambda: demo.film(draw),
)
