"""Snowfall: soft round flakes falling at a range of depths, near ones bigger,
brighter and faster than far ones, each swaying gently side to side."""
import math
import random

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def snowflakes(t, w, h, count=160, seed=0, speed=120.0, size=6.0, sway=24.0, wind=0.0):
    """The flakes at time `t` seconds over a `w` x `h` frame, as `(x, y, r,
    alpha)` tuples drawn back to front. Each flake has a depth: the nearest
    fall at `speed` px/s with radius `size`, the farthest at a quarter of
    that, smaller and dimmer. Each sways up to `sway` px on its own slow
    rhythm and drifts `wind` px/s sideways; flakes wrap around the frame, so
    any `t` (negative too) gives a full, steady fall. The same `seed` gives
    the same flakes."""
    rnd = random.Random(f'snowfall:{seed}')
    out = []
    for _ in range(count):
        z = rnd.random() ** 1.6  # most flakes far away, a few close up
        x0, y0 = rnd.uniform(0, w), rnd.uniform(0, h)
        freq, ph = rnd.uniform(0.25, 0.7), rnd.uniform(0, 2 * math.pi)
        near = 0.25 + 0.75 * z
        r = size * near * rnd.uniform(0.8, 1.2)
        span_y, span_x = h + 4 * r, w + 4 * r + 2 * sway
        y = (y0 + speed * near * t) % span_y - 2 * r
        x = (x0 + wind * near * t) % span_x - 2 * r - sway
        x += sway * near * math.sin(2 * math.pi * freq * t + ph)
        out.append((z, x, y, r, 0.35 + 0.65 * near))
    out.sort(key=lambda f: f[0])
    return [f[1:] for f in out]


def draw_snowfall(cv, t, color='#ffffff', w=None, h=None, **kw):
    """Draw the snow at time `t` seconds over the canvas (or a `w` x `h`
    area from its origin) as soft-edged dots in `color`. `kw` goes to
    `snowflakes` (`count`, `seed`, `speed`, `size`, `sway`, `wind`). Layer
    it over any scene; call it every frame with the film's time."""
    c = cv.ctx
    red, green, blue, a = vb.canvas.rgba(color)
    for x, y, r, alpha in snowflakes(t, w or cv.width, h or cv.height, **kw):
        g = cairo.RadialGradient(x, y, 0, x, y, r * 1.6)
        g.add_color_stop_rgba(0, red, green, blue, a * alpha)
        g.add_color_stop_rgba(0.45, red, green, blue, a * alpha * 0.85)
        g.add_color_stop_rgba(1, red, green, blue, 0)
        c.new_path()
        c.arc(x, y, r * 1.6, 0, 2 * math.pi)
        c.set_source(g)
        c.fill()


def draw(n, cv):
    t = n / demo.FPS
    sky = cairo.LinearGradient(0, 0, 0, demo.H)
    sky.add_color_stop_rgb(0, 0.07, 0.09, 0.14)
    sky.add_color_stop_rgb(1, 0.13, 0.16, 0.23)
    cv.ctx.rectangle(0, 0, demo.W, demo.H)
    cv.ctx.set_source(sky)
    cv.ctx.fill()
    draw_snowfall(cv, t + 4.0, count=220, seed=3, size=9.0)
    cv.mark('snow', 0, 0, demo.W, demo.H)


TECHNIQUE = Technique(
    id='snowfall',
    name='Snowfall',
    family='particles',
    group='Emitters',
    aliases=('falling snow', 'snow particles', 'snow overlay'),
    definition='Soft white dots drift down the frame at different depths, the closer ones larger, '
               'brighter and quicker, each wobbling a little from side to side as it falls.',
    phrasings=('make it snow over the shot',
               'gentle snowflakes falling in the background',
               'add a winter snow overlay'),
    related=('static-noise', 'frost', 'koch-snowflake', 'falling-sand', 'fractal-brownian-motion',
             'noise-terrain-flyover'),
    api=('videobuilder.techniques.particles.snowfall.draw_snowfall',
         'videobuilder.techniques.particles.snowfall.snowflakes'),
    demo=lambda: demo.film(draw),
)
