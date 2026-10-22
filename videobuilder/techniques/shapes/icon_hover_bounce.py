"""Icon Hover Bounce: the moment a pointer lands on an icon, the icon gives a
quick springy pop -- it swells and rocks, then wobbles back to rest -- the
small "I'm alive" reply of a button to a hover or a tap."""
import math
from contextlib import contextmanager

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def kick(t, hz=2.6, ratio=0.28):
    """A damped spring struck once at `t` = 0 seconds: 0 at rest, a first
    swing up to 1, then smaller and smaller swings either side of 0. `hz` is
    how fast it wobbles, `ratio` its damping (lower wobbles longer)."""
    if t <= 0:
        return 0.0
    w0 = 2 * math.pi * hz
    zeta = min(max(ratio, 0.0), 0.95)
    wd = w0 * math.sqrt(1 - zeta * zeta)
    first = math.atan(math.sqrt(1 - zeta * zeta) / zeta) / wd if zeta else math.pi / (2 * wd)  # first peak
    norm = math.exp(-zeta * w0 * first) * math.sin(wd * first)
    return math.exp(-zeta * w0 * t) * math.sin(wd * t) / norm


def icon_hover_bounce(t, pop=0.22, tilt=16.0, hz=2.6, ratio=0.28):
    """The icon's (scale, angle in radians) `t` seconds after the hover or tap
    began: scale pops up by about `pop` and springs back to 1, while the icon
    rocks by about `tilt` degrees and wobbles back to upright. Before `t` = 0
    it is (1.0, 0.0), at rest."""
    s = 1 + pop * kick(t, hz, ratio)
    a = math.radians(tilt) * kick(t, hz * 1.6, ratio * 0.8)
    return s, a


@contextmanager
def bounced(cv, cx, cy, t, **kw):
    """Draw the icon inside this block, centred on (cx, cy) as at rest; it is
    scaled and rotated about that point by `icon_hover_bounce(t, **kw)`."""
    s, a = icon_hover_bounce(t, **kw)
    c = cv.ctx
    c.save()
    c.translate(cx, cy)
    c.rotate(a)
    c.scale(s, s)
    c.translate(-cx, -cy)
    try:
        yield cv
    finally:
        c.restore()


def _bell(cv, cx, cy, size, color):
    """A notification bell centred on (cx, cy), `size` px tall."""
    c, u = cv.ctx, size / 100
    c.save()
    c.translate(cx, cy)
    c.scale(u, u)
    c.new_path()
    c.move_to(-40, 26)
    c.curve_to(-30, 14, -30, 4, -30, -10)
    c.curve_to(-30, -32, -16, -42, 0, -42)
    c.curve_to(16, -42, 30, -32, 30, -10)
    c.curve_to(30, 4, 30, 14, 40, 26)
    c.close_path()
    c.set_source_rgba(*vb.rgba(color))
    c.fill()
    c.arc(0, -44, 7, 0, 2 * math.pi)
    c.fill()
    c.arc(0, 32, 11, 0, math.pi)
    c.fill()
    c.restore()


def _pointer(cv, x, y, size=34):
    """An arrow mouse pointer with its tip at (x, y)."""
    c, u = cv.ctx, size / 24
    pts = [(0, 0), (0, 21), (5, 16.5), (8.5, 24), (12, 22.5), (8.5, 15.5), (15, 15.5)]
    c.save()
    c.translate(x, y)
    c.scale(u, u)
    c.new_path()
    for i, (px, py) in enumerate(pts):
        (c.move_to if i == 0 else c.line_to)(px, py)
    c.close_path()
    c.set_source_rgba(*vb.rgba(demo.INK))
    c.fill_preserve()
    c.set_line_width(1.4)
    c.set_source_rgba(*vb.rgba('#000000'))
    c.stroke()
    c.restore()


HOVER = 1.05  # seconds: when the pointer reaches the icon


def draw(n, cv):
    t = n / demo.FPS
    cx, cy, r = demo.W / 2, demo.H / 2, 82
    on = demo.phase(n, HOVER - 0.1, HOVER + 0.1)  # the button lights up as the pointer arrives
    demo.dot(cv, cx, cy, r, color=demo.LINE, alpha=0.6 + 0.4 * on)
    cv.arc(cx, cy, r, 0, 2 * math.pi, demo.MUTED, width=2, alpha=0.25 + 0.35 * on)
    with bounced(cv, cx, cy, t - HOVER):
        _bell(cv, cx, cy, 96, '#f2b705')
    cv.mark('icon', cx - r, cy - r, 2 * r, 2 * r)
    p = vb.ease_out_quint(demo.phase(n, 0.2, HOVER))
    x0, y0, x1, y1 = cx + 250, cy + 170, cx + 30, cy + 36
    _pointer(cv, x0 + (x1 - x0) * p, y0 + (y1 - y0) * p)


TECHNIQUE = Technique(
    id='icon-hover-bounce',
    name='Icon hover bounce',
    family='shapes',
    group='Icon animation',
    aliases=('hover pop icon', 'micro-interaction bounce', 'icon tap response'),
    definition='When the pointer reaches an icon, the icon briefly swells and rocks, '
               'then wobbles back to its resting size and angle on a short spring.',
    phrasings=('make the icon jiggle when the mouse goes over it',
               'give the button a little springy pop when it is tapped',
               'the bell should wiggle when you hover it'),
    related=('hover-reveal-actions', 'circle-pop', 'hover-lift', 'bounce-ease-in', 'bouncing-dots',
             'image-hover-zoom'),
    api=('videobuilder.techniques.shapes.icon_hover_bounce.icon_hover_bounce',
         'videobuilder.techniques.shapes.icon_hover_bounce.bounced'),
    demo=lambda: demo.film(draw),
)
