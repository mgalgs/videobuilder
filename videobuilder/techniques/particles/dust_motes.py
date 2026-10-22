"""Dust motes: a scatter of tiny specks hanging in still air, each drifting
and wandering slowly, glinting brighter where a shaft of light crosses them."""
import math
import random

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def light_shaft(cv, x, width, angle=0.3, color='#fff4dc', alpha=0.12):
    """A soft beam of light across the whole frame: a band `width` px wide
    whose centre crosses the frame's top edge at `x`, leaning `angle` radians
    from vertical (positive leans right going down), brightest along its
    middle and fading to nothing at both edges."""
    c = cv.ctx
    reach = math.hypot(cv.width, cv.height) * 2
    c.save()
    c.translate(x, 0)
    c.rotate(-angle)
    g = cairo.LinearGradient(-width / 2, 0, width / 2, 0)
    for stop, a in ((0, 0), (0.5, alpha), (1, 0)):
        g.add_color_stop_rgba(stop, *vb.canvas.rgba(color, a))
    c.rectangle(-width / 2, -reach, width, 2 * reach)
    c.set_source(g)
    c.fill()
    c.restore()


def shaft_light(px, py, x, width, angle=0.3):
    """How lit the point (px, py) is by a `light_shaft(cv, x, width, angle)`:
    1 on the beam's centre line, falling smoothly to 0 past its edges."""
    d = (px - x - py * math.tan(angle)) * math.cos(angle)  # distance across the beam
    return math.exp(-(d / (width * 0.35)) ** 2)


def motes(t, w, h, count=160, seed=0, drift=(6.0, -10.0), wander=18.0):
    """The motes at time `t` seconds in a `w` x `h` field, as `(x, y, depth,
    twinkle)` tuples. `depth` runs 0 (far) to 1 (near); nearer motes are
    larger and move faster. Each drifts by `drift` px/s (scaled by depth),
    meanders up to `wander` px on slow independent sines, and wraps at the
    field's edges. `twinkle` (0 -> 1) is a slow per-mote shimmer. The same
    `seed` and `t` always give the same motes."""
    rnd = random.Random(seed)
    out = []
    for _ in range(count):
        x0, y0, depth = rnd.uniform(0, w), rnd.uniform(0, h), rnd.random() ** 1.5
        fx, fy, ft = rnd.uniform(0.15, 0.5), rnd.uniform(0.12, 0.4), rnd.uniform(0.8, 2.5)
        ph = [rnd.uniform(0, 2 * math.pi) for _ in range(3)]
        speed = 0.4 + 0.8 * depth
        x = x0 + drift[0] * speed * t + wander * speed * math.sin(fx * 2 * math.pi * t + ph[0])
        y = y0 + drift[1] * speed * t + wander * speed * math.sin(fy * 2 * math.pi * t + ph[1])
        out.append((x % w, y % h, depth, 0.5 + 0.5 * math.sin(ft * t + ph[2])))
    return out


def dust_motes(cv, t, count=160, seed=0, color='#fff4dc', shaft=None, size=(1.2, 4.5), base=0.12,
               drift=(6.0, -10.0), wander=18.0):
    """Draw floating dust over the whole canvas at time `t` seconds (see
    `motes`). `shaft` is `(x, width, angle)` of a `light_shaft` the dust sits
    in: motes inside it glow up to full strength, motes outside stay at
    `base`; without one every mote is lit. `size` is the radius range far to
    near; near motes get a soft halo."""
    c = cv.ctx
    r_far, r_near = size
    for x, y, depth, tw in motes(t, cv.width, cv.height, count, seed, drift, wander):
        lit = shaft_light(x, y, *shaft) if shaft else 1.0
        a = (base + (1 - base) * lit) * (0.45 + 0.55 * tw) * (0.5 + 0.5 * depth)
        if a < 0.01:
            continue
        r = r_far + (r_near - r_far) * depth
        g = cairo.RadialGradient(x, y, 0, x, y, r * 3)
        g.add_color_stop_rgba(0, *vb.canvas.rgba(color, a))
        g.add_color_stop_rgba(0.33, *vb.canvas.rgba(color, a * 0.6))
        g.add_color_stop_rgba(1, *vb.canvas.rgba(color, 0))
        c.new_path()
        c.arc(x, y, r * 3, 0, 2 * math.pi)
        c.set_source(g)
        c.fill()


SHAFT = (demo.W * 0.38, 520, 0.32)


def draw(n, cv):
    t = n / demo.FPS
    light_shaft(cv, SHAFT[0], SHAFT[1], SHAFT[2], alpha=0.10)
    light_shaft(cv, SHAFT[0] + 40, SHAFT[1] * 0.45, SHAFT[2], alpha=0.07)
    dust_motes(cv, t + 4.0, count=220, seed=3, shaft=SHAFT)
    cv.mark('dust', 0, 0, demo.W, demo.H)


TECHNIQUE = Technique(
    id='dust-motes',
    name='Dust motes',
    family='particles',
    group='Emitters',
    aliases=('floating dust', 'light shaft particles', 'airborne dust'),
    definition='Tiny bright specks float lazily in the air, wandering and glinting as they pass through a '
               'beam of light.',
    phrasings=('little bits of dust floating in a sunbeam',
               'specks drifting slowly in the light like a quiet attic',
               'add some floating dust particles to the shot'),
    related=('lens-dirt-overlay', 'film-grain', 'layered-fog-bands', 'heat-haze', 'falling-sand',
             'dust-and-scratches'),
    api=('videobuilder.techniques.particles.dust_motes.dust_motes',
         'videobuilder.techniques.particles.dust_motes.light_shaft',
         'videobuilder.techniques.particles.dust_motes.motes'),
    demo=lambda: demo.film(draw),
)
