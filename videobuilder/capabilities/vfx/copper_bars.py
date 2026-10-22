"""Copper Bars: full-width horizontal bands, each shaded dark at its edges
and white-hot along its middle so it reads as a lit metal tube, swing up and
down the frame on staggered sine paths and pass in front of and behind each
other -- the old home-computer trick of changing the palette per scanline."""
import math

import cairo

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Technique

# The demo's bars, top of the stack first: copper, magenta, sky, gold, violet, mint.
COLORS = ('#e2793b', '#e0457b', '#4fa6ef', '#f2c230', '#8f6cf0', '#3fd6a4')


def copper_bar(cv, y, h, color, x=0.0, w=None, glow=0.6, alpha=1.0):
    """One copper bar: a band `h` px tall centred on `y`, from `x` across `w`
    (default the canvas width). Its shading runs from near-black at both
    edges through `color` to almost white at the centre line, like a
    cylinder lit from the front. `glow` (0 for none) adds a soft halo of
    `color` above and below, as a fraction of `h`."""
    w = cv.width - x if w is None else w
    r, g, b, _ = rgba(color)
    c = cv.ctx
    top = y - h / 2
    if glow > 0:
        gh = h * glow
        halo = cairo.LinearGradient(0, top - gh, 0, top + h + gh)
        halo.add_color_stop_rgba(0, r, g, b, 0)
        halo.add_color_stop_rgba(0.5, r, g, b, 0.35 * alpha)
        halo.add_color_stop_rgba(1, r, g, b, 0)
        c.rectangle(x, top - gh, w, h + 2 * gh)
        c.set_source(halo)
        c.fill()
    grad = cairo.LinearGradient(0, top, 0, top + h)
    for k in range(9):
        s = k / 8
        lit = math.sin(math.pi * s)  # 0 at the edges, 1 in the middle
        dark = 0.15 + 0.85 * min(1.0, lit * 1.6)
        white = max(0.0, lit - 0.75) / 0.25 * 0.8  # a white highlight only near the centre line
        grad.add_color_stop_rgba(s, *(v * dark + (1 - v * dark) * white for v in (r, g, b)), alpha)
    c.rectangle(x, top, w, h)
    c.set_source(grad)
    c.fill()
    return vb.Box(x, top, w, h)


def copper_bars(cv, t, colors=COLORS, center=None, amplitude=None, h=None, speed=1.0, spread=0.55,
                x=0.0, w=None, glow=0.6, alpha=1.0):
    """A stack of copper bars, one per colour in `colors`, at time `t`
    seconds. Each swings about `center` (default mid-frame) by `amplitude`
    px (default 0.32 of the height) on a sine whose phase trails the bar
    before by `spread` radians, so the stack ripples like a chain; `speed`
    scales the motion. Bars on the near half of their cycle draw in front,
    so they weave over and under each other. `h` is each bar's thickness
    (default 1/11 of the height). Returns the bars' Boxes, top-drawn last."""
    H = cv.height
    center = H / 2 if center is None else center
    amplitude = H * 0.32 if amplitude is None else amplitude
    h = H / 11 if h is None else h
    bars = []
    for i, color in enumerate(colors):
        a = t * speed * 2.2 - i * spread
        bars.append((math.cos(a), center + amplitude * math.sin(a), color))
    bars.sort(key=lambda b: b[0])  # furthest (cos lowest) first, so the near ones cover them
    return [copper_bar(cv, y, h, color, x=x, w=w, glow=glow, alpha=alpha) for _, y, color in bars]


def draw(n, cv):
    t = n / demo.FPS
    boxes = copper_bars(cv, t, speed=1.0)
    for i, box in enumerate(boxes):
        cv.mark(f'bar{i}', *box)


TECHNIQUE = Technique(
    id='copper-bars',
    name='Copper bars',
    family='vfx',
    group='Retro digital',
    aliases=('raster bars', 'demoscene bars', 'gradient bars'),
    definition='Shiny horizontal stripes, each shaded like a lit tube, stretch across the whole screen '
               'and swing up and down on rippling sine paths, crossing over and under one another.',
    phrasings=('those glowing rainbow bars bouncing up and down like an old Amiga demo',
               'a retro computer intro with shiny horizontal stripes waving behind the logo',
               'chrome-looking colour bands that weave over each other across the screen'),
    related=('refresh-bar', 'audio-waveform-bars', 'striped-progress-bar', 'vhs-tracking-bar', 'letterbox',
             'ridgeline-ripple'),
    api=('videobuilder.techniques.vfx.copper_bars.copper_bars',
         'videobuilder.techniques.vfx.copper_bars.copper_bar'),
    demo=lambda: demo.film(draw),
)
