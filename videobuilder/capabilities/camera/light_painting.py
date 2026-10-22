"""Light painting: a bright point moves through a dark frame and everything it
has passed stays lit behind it, as if the shutter were held open."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

# (extra width, alpha) of each stroke, widest and faintest first: the soft
# bloom around the trail, then the core, then a near-white hot centre.
HALO = ((26, 0.05), (14, 0.10), (6, 0.22), (0, 1.0))


def _glow(cv, cx, cy, r, color, alpha):
    g = cairo.RadialGradient(cx, cy, 0, cx, cy, r)
    cr, cg, cb, _ = vb.rgba(color)
    g.add_color_stop_rgba(0, cr, cg, cb, alpha)
    g.add_color_stop_rgba(1, cr, cg, cb, 0)
    cv.ctx.rectangle(cx - r, cy - r, 2 * r, 2 * r)
    cv.ctx.set_source(g)
    cv.ctx.fill()


def light_painting(cv, points, p, color='#ffc93c', width=5, head=1.0, core='#fff6d8', closed=False):
    """Draw the light trail at progress `p` (0 -> 1): the leading `p` of the
    point list `points` (by arc length) as a glowing stroke `width` px wide,
    with the light source itself burning at the tip. The light adds onto
    what is underneath, so crossings brighten, as on a long exposure.

    `head` scales the light source's glow (0 hides it, e.g. once the light
    has gone off). `core` is the hot centre of the stroke. Returns the
    tip's (x, y), or None before the trail starts."""
    trail = vb.paths.reveal(points, p, closed=closed)
    if len(trail) < 2:
        return None
    c = cv.ctx
    c.save()
    c.set_operator(cairo.OPERATOR_ADD)
    for extra, alpha in HALO:
        vb.paths.draw(cv, trail, color, width=width + extra, alpha=alpha)
    vb.paths.draw(cv, trail, core, width=max(1.0, width * 0.35), alpha=0.8)
    x, y = trail[-1]
    if head > 0:
        _glow(cv, x, y, 60 * head, color, 0.45)
        _glow(cv, x, y, 16 * head, core, 0.9)
    c.restore()
    return x, y


def _loops(n=700):
    """A run of cursive loops across the frame, like a sparkler signature."""
    out = []
    for i in range(n):
        t = i / (n - 1)
        a = t * 4.5 * 2 * math.pi - math.pi / 2
        r = 120 + 30 * math.sin(t * math.pi)
        out.append((demo.W * 0.17 + t * demo.W * 0.6 + r * math.cos(a),
                    demo.H / 2 + 40 * math.sin(t * 2 * math.pi) + r * math.sin(a)))
    return out


POINTS = _loops()


def draw(n, cv):
    p = demo.phase(n, 0.2, 2.6)  # a hand-held light moves at an even pace
    head = 1 - demo.phase(n, 2.6, 2.85)
    tip = light_painting(cv, POINTS, p, head=head)
    if tip:
        cv.mark('light', tip[0] - 20, tip[1] - 20, 40, 40)


TECHNIQUE = Technique(
    id='light-painting',
    name='Light painting',
    family='camera',
    group='Lighting & surface',
    aliases=('long-exposure light trails', 'light paint', 'light streaks', 'time-exposure trails'),
    definition='A glowing point of light sweeps across a dark frame and leaves an unbroken bright line '
               'everywhere it has been, the way a slow shutter records a moving torch.',
    phrasings=('draw a glowing line with a moving light, like a sparkler photo',
               'a light that leaves a lasting trail behind it as it moves',
               'make it look like someone wrote in the air with a torch on a long exposure'),
    related=('light-trail-logo-reveal', 'multiples', 'phosphor-persistence', 'paint-brush-wipe',
             'long-shadow-extension', 'long-shadow-growth'),
    api=('videobuilder.techniques.camera.light_painting.light_painting',
         'videobuilder.paths.reveal'),
    demo=lambda: demo.film(draw),
)
