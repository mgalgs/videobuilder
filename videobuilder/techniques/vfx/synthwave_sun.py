"""Synthwave Sun: the 80s retro-futurist sunset -- a big disc shaded from
hot yellow to magenta, sitting on the horizon, its lower half sliced by
horizontal gaps that widen toward the bottom and drift slowly downward."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..particles.wireframe_terrain import wireframe_terrain
from ..schema import Technique

SUN_TOP, SUN_BOTTOM = '#ffe95c', '#ff2a7a'
SKY_TOP, SKY_HORIZON = '#12062b', '#7a1f6e'


def sun_bands(top, bottom, t=0.0, start=0.45, slices=7, min_gap=0.08, max_gap=0.75, speed=0.35):
    """The solid (y0, y1) spans of a sun running from `top` to `bottom` (y
    pixels) once its slices are cut. Slicing begins `start` of the way down;
    below that, `slices` evenly pitched gaps grow from `min_gap` to `max_gap`
    of their pitch toward the bottom. The gaps slide down `speed` pitches a
    second at time `t` (seconds), new ones opening at the top of the cut, so
    calling it every frame with a rising `t` scrolls them."""
    cut = top + (bottom - top) * start
    pitch = (bottom - cut) / slices
    offset = (t * speed) % 1.0
    spans, y = [], top
    for k in range(-1, slices + 1):
        mid = cut + (k + offset) * pitch  # gap centre
        depth = vb.clamp01((mid - cut) / (bottom - cut))
        half = pitch * (min_gap + (max_gap - min_gap) * depth) / 2
        g0, g1 = max(mid - half, cut), min(mid + half, bottom)
        if g1 <= g0:
            continue
        if g0 > y:
            spans.append((y, g0))
        y = max(y, g1)
    if y < bottom:
        spans.append((y, bottom))
    return spans


def synthwave_sun(cv, cx, horizon, r, t=0.0, rise=1.0, lift=0.4, top=SUN_TOP, bottom=SUN_BOTTOM, glow=0.55,
                  alpha=1.0, **slicing):
    """Draw a retro sliced sun of radius `r` centred at `cx`, resting on the
    `horizon` line (y pixels): nothing below the horizon is drawn. `rise`
    0 -> 1 lifts it from fully set to its usual pose, centre `lift` * `r`
    above the horizon. The slices are laid over the visible part. A vertical
    gradient runs `top` -> `bottom` across the disc, a soft halo of strength
    `glow` sits behind it, and the lower half is cut into slices that scroll
    with `t` (seconds); `slicing` passes through to `sun_bands`."""
    cy = horizon + r - r * (1 + lift) * rise
    lo = min(cy + r, horizon)
    hi = cy - r
    if lo <= hi:
        return
    c = cv.ctx
    with cv.clip(0, 0, cv.width, horizon):
        if glow > 0:
            g = cairo.RadialGradient(cx, cy, r * 0.6, cx, cy, r * 1.9)
            g.add_color_stop_rgba(0, *vb.canvas.rgba(bottom, glow * alpha)[:3], glow * alpha)
            g.add_color_stop_rgba(1, *vb.canvas.rgba(bottom, 0)[:3], 0)
            c.set_source(g)
            c.paint()
        grad = cairo.LinearGradient(0, hi, 0, lo)
        grad.add_color_stop_rgba(0, *vb.canvas.rgba(top, alpha))
        grad.add_color_stop_rgba(1, *vb.canvas.rgba(bottom, alpha))
        c.save()
        c.new_path()
        c.arc(cx, cy, r, 0, 2 * math.pi)
        c.clip()
        c.new_path()
        for y0, y1 in sun_bands(hi, lo, t, **slicing):
            y0, y1 = max(y0, hi), min(y1, lo)
            if y1 > y0:
                c.rectangle(cx - r, y0, 2 * r, y1 - y0)
        c.set_source(grad)
        c.fill()
        c.restore()


def draw(n, cv):
    t = n / demo.FPS
    horizon = demo.H * 0.62
    c = cv.ctx
    sky = cairo.LinearGradient(0, 0, 0, horizon)
    sky.add_color_stop_rgb(0, *vb.canvas.rgba(SKY_TOP)[:3])
    sky.add_color_stop_rgb(1, *vb.canvas.rgba(SKY_HORIZON)[:3])
    c.rectangle(0, 0, demo.W, horizon)
    c.set_source(sky)
    c.fill()
    r = demo.H * 0.36
    synthwave_sun(cv, demo.W / 2, horizon, r, t, rise=0.6 + 0.4 * vb.ease_out_quint(demo.phase(n, 0, 1.4)))
    cv.rect(0, horizon, demo.W, demo.H - horizon, '#0b0420')
    floor = vb.Box(0, horizon, demo.W, demo.H - horizon)
    wireframe_terrain(cv, t, box=floor, color='#ff3fb4', relief=0.0, horizon=0.0, camera=1.0, cols=120, rows=90, width=2.0)
    cv.line(0, horizon, demo.W, horizon, '#ff7ad1', width=3)
    cv.mark('sun', demo.W / 2 - r, horizon - r, 2 * r, r)


TECHNIQUE = Technique(
    id='synthwave-sun',
    name='Synthwave sun',
    family='vfx',
    group='Retro digital',
    aliases=('retro sunset', 'striped sun', 'outrun sun', 'vaporwave sun'),
    definition='A huge yellow-to-pink sun half sunk behind the horizon, its lower part cut into '
               'horizontal bars that thicken and slide downward, glowing over a neon 80s sky.',
    phrasings=('that 80s retro sunset with the stripes through the sun',
               'an outrun-style sun over a neon grid',
               'a vaporwave sun sliced into bars on the horizon'),
    related=('day-night-cycle', 'meteor-shower', 'sunburst-build', 'aurora-gradient-background',
             'solarization', 'lens-flare'),
    api=('videobuilder.techniques.vfx.synthwave_sun.synthwave_sun',
         'videobuilder.techniques.vfx.synthwave_sun.sun_bands'),
    demo=lambda: demo.film(draw),
)
