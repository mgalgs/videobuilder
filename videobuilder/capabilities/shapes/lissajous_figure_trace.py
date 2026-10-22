"""Lissajous Figure Trace: a pen driven by two oscillators at right angles,
one sideways and one up and down, draws a looping knot whose shape is set
by the ratio of their speeds."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def lissajous(cx, cy, rx, ry, fx=3, fy=2, phase=math.pi / 2, p=1.0, turns=1.0, damping=0.0, samples=720):
    """The curve x = sin(fx t + phase), y = sin(fy t), centred at (cx, cy)
    and spanning `rx` by `ry` px either side, as a point list from t = 0 up
    to progress `p` (0 -> 1) of `turns` full cycles (2 pi each). `damping`
    shrinks both swings by exp(-damping t / 2 pi), so a value like 0.15
    spirals inward like a harmonograph. The pen sits at the last point."""
    end = 2 * math.pi * turns * vb.clamp01(p)
    count = max(2, round(samples * turns * vb.clamp01(p)))
    out = []
    for i in range(count + 1):
        t = end * i / count
        k = math.exp(-damping * t / (2 * math.pi))
        out.append((cx + rx * k * math.sin(fx * t + phase), cy - ry * k * math.sin(fy * t)))
    return out


def draw_lissajous_trace(cv, cx, cy, rx, ry, p, fx=3, fy=2, phase=math.pi / 2, color=demo.INK, width=3,
                         pen=demo.ACCENT, guides=True, turns=1.0, damping=0.0):
    """Draw the Lissajous curve traced up to progress `p` (see `lissajous`),
    with the pen as a dot at its tip. `guides`: also draw the two driving
    oscillators -- a dot sliding along a track above the figure (x) and one
    beside it (y) -- with dotted lines projecting them onto the pen. Returns
    the pen's (x, y)."""
    pts = lissajous(cx, cy, rx, ry, fx, fy, phase, p, turns, damping)
    px, py = pts[-1]
    if guides:
        top, left = cy - ry - 50, cx - rx - 70
        cv.line(cx - rx, top, cx + rx, top, demo.LINE, width=2)
        cv.line(left, cy - ry, left, cy + ry, demo.LINE, width=2)
        _dotted(cv, px, top, px, py)
        _dotted(cv, left, py, px, py)
        demo.dot(cv, px, top, r=8, color=demo.TEAL)
        demo.dot(cv, left, py, r=8, color=demo.TEAL)
    vb.paths.draw(cv, pts, color, width=width)
    if pen:
        demo.dot(cv, px, py, r=14, color=pen, alpha=0.3)
        demo.dot(cv, px, py, r=7, color=pen)
    return px, py


def _dotted(cv, x0, y0, x1, y1, step=8):
    hops = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
    for i in range(0, hops, 2):
        a, b = i / hops, min(1, (i + 1) / hops)
        cv.line(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a, x0 + (x1 - x0) * b, y0 + (y1 - y0) * b,
                demo.MUTED, width=1.5, alpha=0.7)


def draw(n, cv):
    p = demo.phase(n, 0.2, 2.7)
    draw_lissajous_trace(cv, demo.W / 2 + 35, demo.H / 2 + 25, 250, 185, p)


CAPABILITY = Capability(
    id='lissajous-figure-trace',
    name='Lissajous figure trace',
    family='shapes',
    group='Geometric motion',
    aliases=('Lissajous curve', 'Lissajous figure', 'Bowditch curve', 'harmonograph', 'parametric curve trace',
             'pendulum drawing'),
    definition='A pen pushed by one side-to-side wave and one up-and-down wave at different speeds '
               'draws a looping, knotted curve as it goes.',
    phrasings=('draw one of those looping oscilloscope figure-eight patterns',
               'a dot traces a woven loop from two swinging motions',
               'show a harmonograph-style curve drawing itself'),
    related=('map-route-draw', 'rotoscope-look', 'bezier-handle-bend', 'parallel-coordinates-draw',
             'scroll-drawn-svg-path', 'cycle-diagram-rotation'),
    api=('videobuilder.capabilities.shapes.lissajous_figure_trace.draw_lissajous_trace',
         'videobuilder.capabilities.shapes.lissajous_figure_trace.lissajous'),
    demo=lambda: demo.film(draw),
)
