"""Animated gradient sweep: a band of colours that slides steadily across a
shape, so the fill seems to flow in one direction and loops without a seam."""
import math

import cairo

from .. import _demo as demo
from ...canvas import rgba
from ..schema import Technique

SWEEP_COLORS = ('#ef5b4c', '#f2a65a', '#4fc3b0', '#6c63ff')


def gradient_sweep(cv, x, y, w, h, t, colors=SWEEP_COLORS, angle=20.0, period=None, radius=0, alpha=1.0):
    """Fill the box (x, y, w, h) with a repeating linear gradient through
    `colors` (and back to the first), shifted by `t` periods along `angle`
    degrees (0 runs left to right, positive tilts it down). Animate `t` -- say
    `n / fps / seconds` -- and the colours sweep across the box; any whole
    number of periods loops seamlessly. `period` is the length of one full
    cycle of colours in px (default the box's width)."""
    period = period or w
    a = math.radians(angle)
    dx, dy = math.cos(a), math.sin(a)
    cx, cy = x + w / 2, y + h / 2
    shift = (t % 1.0) * period
    x0, y0 = cx + dx * shift, cy + dy * shift
    grad = cairo.LinearGradient(x0, y0, x0 + dx * period, y0 + dy * period)
    grad.set_extend(cairo.EXTEND_REPEAT)
    stops = tuple(colors) + (colors[0],)
    for i, c in enumerate(stops):
        grad.add_color_stop_rgba(i / (len(stops) - 1), *rgba(c, alpha))
    with cv.clip(x, y, w, h, radius):
        cv.ctx.set_source(grad)
        cv.ctx.paint()


def draw(n, cv):
    w, h = demo.W * 0.72, demo.H * 0.6
    x, y = (demo.W - w) / 2, (demo.H - h) / 2
    cv.shadow(x, y, w, h, radius=24, dy=10, blur=28, color=(0, 0, 0, 0.5))
    gradient_sweep(cv, x, y, w, h, n / demo.FPS / demo.SECONDS, radius=24, period=w * 0.9)
    cv.mark('panel', x, y, w, h)


TECHNIQUE = Technique(
    id='animated-gradient-sweep',
    name='Animated gradient sweep',
    family='shapes',
    group='Gradients & color',
    aliases=('moving gradient', 'flowing gradient', 'gradient animation', 'scrolling gradient'),
    definition='A multi-colour gradient fill whose colours keep sliding across a shape in one direction, '
               'so the surface looks like it is flowing.',
    phrasings=('make the background colours slowly slide across',
               'a gradient that moves across the box on a loop',
               'shift the colours of the fill sideways over time'),
    related=('gradient-shift-button', 'gradient-sweep-across-text', 'swirl', 'gradient-border-spin',
             'isolines-contour-animation', 'aurora-gradient-background'),
    api=('videobuilder.techniques.shapes.animated_gradient_sweep.gradient_sweep',),
    demo=lambda: demo.film(draw),
)
