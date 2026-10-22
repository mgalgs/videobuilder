"""Custom Cubic-Bezier Easing: videobuilder already has it as `vb.bezier`
(CSS `cubic-bezier(x1, y1, x2, y2)`), so this entry only names it and demos
it: the curve with its two handles, and a dot riding that curve."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

HANDLES = (0.6, -0.35, 0.25, 1.35)  # pulls back first, then overshoots: plainly not a stock curve
ease = vb.bezier(*HANDLES)

GX, GY, G = 250, 130, 280  # the graph: progress 0 -> 1 left to right, value 0 -> 1 bottom to top
TRACK_X = 720


def at(x, y):
    """Graph units -> frame px."""
    return GX + x * G, GY + G - y * G


def draw(n, cv):
    p = demo.phase(n, 0.5, 2.3)
    v = ease(p)
    x1, y1, x2, y2 = HANDLES
    (ax, ay), (bx, by) = at(0, 0), at(1, 1)
    (h1x, h1y), (h2x, h2y) = at(x1, y1), at(x2, y2)

    cv.outline(GX, GY, G, G, demo.LINE, width=2)
    cv.line(ax, ay, bx, by, demo.MUTED, width=1, alpha=0.35)  # linear, for comparison
    cv.line(ax, ay, h1x, h1y, demo.MUTED, width=2)
    cv.line(bx, by, h2x, h2y, demo.MUTED, width=2)
    c = cv.ctx
    c.move_to(ax, ay)
    c.curve_to(h1x, h1y, h2x, h2y, bx, by)
    c.set_source_rgba(*vb.rgba(demo.TEAL))
    c.set_line_width(4)
    c.stroke()
    demo.dot(cv, h1x, h1y, 9, color=demo.INK)
    demo.dot(cv, h2x, h2y, 9, color=demo.INK)

    px, py = at(p, v)
    cv.line(px, py, TRACK_X, py, demo.ACCENT, width=1, alpha=0.5)
    demo.dot(cv, px, py, 8, color=demo.ACCENT)

    cv.line(TRACK_X, GY, TRACK_X, GY + G, demo.LINE, width=3)
    for y in (GY, GY + G):
        cv.line(TRACK_X - 18, y, TRACK_X + 18, y, demo.MUTED, width=2)
    demo.dot(cv, TRACK_X, py, 26)
    cv.mark('ball', TRACK_X - 26, py - 26, 52, 52)

    demo.word(cv, 'cubic-bezier(.6, -.35, .25, 1.35)', TRACK_X, 50, size=22,
              color=demo.MUTED, font=demo.mono(22))


TECHNIQUE = Technique(
    id='custom-cubic-bezier-easing',
    name='Custom Cubic-Bezier Easing',
    family='principles',
    group='Easing',
    aliases=('cubic-bezier', 'custom ease', 'bezier easing', 'custom easing curve'),
    definition='A move whose speed follows a curve you shape yourself by dragging two control handles, '
               'so it can lag, rush, pull back or overshoot exactly as you want.',
    phrasings=('use my own easing curve with these four numbers',
               'give it a hand-tuned ease instead of a preset',
               'ease it with cubic-bezier(0.6, -0.35, 0.25, 1.35)'),
    related=('bezier-handle-bend', 'speed-ramp', 'asymmetric-fast-in-slow-out', 'isolines-contour-animation',
             'dragon-curve', 'hilbert-curve'),
    api=('videobuilder.bezier',),
    demo=lambda: demo.film(draw),
)
