"""Embers: small glowing sparks drift up off a fire, wavering on the heat,
cooling from white-hot through orange to dull red as they fade out.

`embers` is stateless: each spark's place and heat is worked out from the
time alone, so any frame renders on its own and the stream loops without a
seam. `draw_embers` draws them with additive glow on the frame."""
import math
import random

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

# heat 1 -> 0: white-hot, yellow, orange, deep red
RAMP = ((1.0, (1.0, 0.97, 0.85)), (0.75, (1.0, 0.82, 0.35)), (0.45, (1.0, 0.45, 0.08)),
        (0.0, (0.55, 0.06, 0.02)))


def ember_color(heat):
    """The (r, g, b) of a spark at `heat` 1 (fresh) -> 0 (spent)."""
    heat = vb.clamp01(heat)
    for (h0, c0), (h1, c1) in zip(RAMP, RAMP[1:]):
        if heat >= h1:
            k = (heat - h1) / (h0 - h1)
            return tuple(b + (a - b) * k for a, b in zip(c0, c1))
    return RAMP[-1][1]


def embers(t, x0, x1, y, count=90, life=2.4, rise=260.0, sway=40.0, wind=0.0, size=4.0, seed=0):
    """The sparks alive at time `t` seconds, as `(x, y, radius, heat, alpha)`.

    They are born at random along the line from (x0, y) to (x1, y), a steady
    `count` per `life` seconds, each living about `life` seconds. Each rises
    at about `rise` px/s, speeding up as the heat lifts it, wanders sideways
    up to `sway` px, drifts `wind` px/s, and starts about `size` px across.
    Heat falls from 1 to 0 over its life; `alpha` flickers and fades out at
    the end. The same `seed` gives the same sparks every time."""
    out = []
    for i in range(count):
        r = random.Random(f'{seed}:{i}')
        span = life * r.uniform(0.6, 1.25)
        offset = r.uniform(0, span)
        cycle, age = divmod(t + offset, span)
        r = random.Random(f'{seed}:{i}:{int(cycle)}')  # a fresh spark each time round
        k = age / span
        bx = x0 + (x1 - x0) * r.random()
        speed = rise * r.uniform(0.6, 1.3)
        wob, freq, ph = sway * r.uniform(0.3, 1.0), r.uniform(1.2, 3.2), r.uniform(0, 2 * math.pi)
        x = bx + wind * age + wob * (math.sin(freq * age + ph) - math.sin(ph)) * min(1.0, age * 2)
        yy = y - speed * age * (1 + 0.6 * k)
        heat = (1 - k) ** 1.3 * r.uniform(0.8, 1.0)
        flicker = 0.75 + 0.25 * math.sin(age * r.uniform(14, 26) + ph * 3)
        alpha = flicker * vb.clamp01(age / 0.12) * vb.clamp01((1 - k) / 0.35)
        radius = size * r.uniform(0.5, 1.4) * (0.45 + 0.55 * (1 - k))
        out.append((x, yy, radius, heat, alpha))
    return out


def draw_embers(cv, sparks, glow=4.0, alpha=1.0):
    """Draw `sparks` (from `embers`) with light that adds up where they
    cross: a hot core and a soft halo `glow` times its radius."""
    c = cv.ctx
    c.save()
    c.set_operator(cairo.OPERATOR_ADD)
    for x, y, radius, heat, a in sparks:
        a *= alpha
        if a <= 0.01:
            continue
        cr, cg, cb = ember_color(heat)
        halo = radius * glow
        g = cairo.RadialGradient(x, y, 0, x, y, halo)
        g.add_color_stop_rgba(0, cr, cg, cb, 0.45 * a)
        g.add_color_stop_rgba(1, cr, cg, cb, 0)
        c.rectangle(x - halo, y - halo, 2 * halo, 2 * halo)
        c.set_source(g)
        c.fill()
        hr, hg, hb = ember_color(min(1.0, heat + 0.3))
        c.new_path()
        c.arc(x, y, radius, 0, 2 * math.pi)
        c.set_source_rgba(hr, hg, hb, a)
        c.fill()
    c.restore()


def _bed(cv, n):
    """A low glow of coals along the bottom of the demo frame, pulsing gently."""
    c = cv.ctx
    pulse = 0.85 + 0.15 * math.sin(n / demo.FPS * 5.0)
    g = cairo.LinearGradient(0, demo.H, 0, demo.H - 320)
    g.add_color_stop_rgba(0, 1.0, 0.35, 0.05, 0.55 * pulse)
    g.add_color_stop_rgba(0.35, 0.8, 0.15, 0.03, 0.22 * pulse)
    g.add_color_stop_rgba(1, 0.5, 0.05, 0.0, 0)
    c.rectangle(0, demo.H - 320, demo.W, 320)
    c.set_source(g)
    c.fill()


def draw(n, cv):
    t = n / demo.FPS + 3.0  # start mid-stream, the air already full of sparks
    _bed(cv, n)
    sparks = embers(t, demo.W * 0.15, demo.W * 0.85, demo.H + 10, count=140, life=2.6, rise=230,
                    sway=55, wind=35, size=5.0, seed=3)
    draw_embers(cv, sparks)


CAPABILITY = Capability(
    id='embers',
    name='Embers',
    family='particles',
    group='Emitters',
    aliases=('rising sparks', 'fire sparks', 'floating embers', 'ember particles'),
    definition='Tiny glowing sparks drift upward as if off a fire, wavering on the heat and cooling '
               'from bright yellow to dim red before they wink out.',
    phrasings=('sparks floating up from a campfire behind the title',
               'glowing bits of ash rising and fading over a dark background',
               'add some drifting fire embers for a warm, smouldering mood'),
    related=('heat-haze', 'lightning-bolt', 'electric-arc', 'gooch-shading', 'diffraction-spikes',
             'line-boil'),
    api=('videobuilder.capabilities.particles.embers.draw_embers',
         'videobuilder.capabilities.particles.embers.embers',
         'videobuilder.capabilities.particles.embers.ember_color'),
    demo=lambda: demo.film(draw),
)
