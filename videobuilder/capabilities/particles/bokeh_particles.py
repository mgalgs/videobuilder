"""Bokeh Particles: a field of big, soft, out-of-focus discs of coloured light
that drift slowly across a dark frame, swelling and fading as they go."""
import math
import random

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

COLORS = ('#e0a83a', '#f2c66b', '#7f8fe0', '#a7b2f0', '#dfe3ea')


def bokeh_disc(cv, cx, cy, r, color, alpha=0.5, softness=0.3):
    """One out-of-focus light at (cx, cy): a flat disc of `color`, a little
    brighter towards its rim like a lens highlight, fading out over the outer
    `softness` of its radius. Blends as light (screen), so overlaps brighten."""
    if r <= 0 or alpha <= 0:
        return
    cr, cg, cb, _ = vb.rgba(color)
    edge = 1 - vb.clamp01(softness)
    g = cairo.RadialGradient(cx, cy, 0, cx, cy, r)
    g.add_color_stop_rgba(0, cr, cg, cb, alpha * 0.7)
    g.add_color_stop_rgba(edge * 0.85, cr, cg, cb, alpha * 0.8)
    g.add_color_stop_rgba(edge, cr, cg, cb, alpha)
    g.add_color_stop_rgba(1, cr, cg, cb, 0)
    ctx = cv.ctx
    ctx.save()
    ctx.set_operator(cairo.OPERATOR_SCREEN)
    ctx.arc(cx, cy, r, 0, 2 * math.pi)
    ctx.set_source(g)
    ctx.fill()
    ctx.restore()


def bokeh_lights(count, width, height, seed=0, colors=COLORS, sizes=(20, 130), drift=50):
    """`count` lights as dicts, fixed by `seed`: where each starts, its radius,
    colour, drift velocity (px/s, up to `drift`, mostly rising) and pulse
    rate. Bigger lights drift slower and dimmer, as if further from focus."""
    rnd = random.Random(seed)
    lights = []
    for _ in range(count):
        k = rnd.random() ** 1.6  # mostly small, a few large
        r = sizes[0] + (sizes[1] - sizes[0]) * k
        speed = drift * (1.1 - 0.6 * k) * rnd.uniform(0.5, 1.0)
        ang = -math.pi / 2 + rnd.uniform(-1.1, 1.1)
        lights.append(dict(x=rnd.uniform(-r, width + r), y=rnd.uniform(-r, height + r), r=r,
                           color=rnd.choice(colors), vx=speed * math.cos(ang), vy=speed * math.sin(ang),
                           alpha=rnd.uniform(0.35, 0.6) * (1 - 0.35 * k),
                           hz=rnd.uniform(0.25, 0.6), ph=rnd.uniform(0, 2 * math.pi)))
    return lights


def draw_bokeh(cv, t, lights, width, height, pulse=0.35, fade=1.0):
    """Draw `lights` (from `bokeh_lights`) at time `t` seconds over a frame
    `width` x `height`: each drifts along its velocity, wrapping round the
    edges, while its brightness and size breathe by up to `pulse`. `fade`
    scales every light's strength, for bringing the field in or out."""
    for b in lights:
        r = b['r']
        x = (b['x'] + b['vx'] * t + r) % (width + 2 * r) - r
        y = (b['y'] + b['vy'] * t + r) % (height + 2 * r) - r
        s = math.sin(2 * math.pi * b['hz'] * t + b['ph'])
        bokeh_disc(cv, x, y, r * (1 + 0.08 * pulse * s), b['color'],
                   alpha=b['alpha'] * (1 + pulse * s) * fade)


LIGHTS = bokeh_lights(38, demo.W, demo.H, seed=11, sizes=(24, 150), drift=90)


def draw(n, cv):
    cv.fill('#0d1016')
    draw_bokeh(cv, n / demo.FPS, LIGHTS, demo.W, demo.H, pulse=0.45, fade=0.4 + 0.6 * demo.phase(n, 0, 0.6))


CAPABILITY = Capability(
    id='bokeh-particles',
    name='Bokeh particles',
    family='particles',
    group='Emitters',
    aliases=('bokeh field', 'out-of-focus light discs', 'bokeh lights'),
    definition='Big blurred circles of coloured light float gently over a dark background, '
               'overlapping and slowly brightening and dimming like city lights seen out of focus.',
    phrasings=('soft blurry circles of light floating in the background',
               'a dreamy out-of-focus lights backdrop behind the title',
               'glowing defocused dots drifting around like fairy lights'),
    related=('bokeh-highlights', 'depth-of-field', 'particle-morph', 'bloom', 'ripple', 'diffraction-spikes'),
    api=('videobuilder.capabilities.particles.bokeh_particles.draw_bokeh',
         'videobuilder.capabilities.particles.bokeh_particles.bokeh_lights',
         'videobuilder.capabilities.particles.bokeh_particles.bokeh_disc'),
    demo=lambda: demo.film(draw),
)
