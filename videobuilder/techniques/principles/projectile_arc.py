"""Projectile Arc: a thrown thing flies on a parabola -- steady sideways
speed, while gravity slows its rise, turns it over at the top and speeds its
fall -- so it lands where it was aimed."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def projectile_arc(x0, y0, x1, y1, peak, t):
    """The point at time `t` in [0, 1] on a thrown object's flight from
    (x0, y0) to (x1, y1) whose highest point is at screen height `peak`
    (y grows downward, so `peak` is the smallest y; it is clamped to no lower
    than the higher end). Sideways motion is linear in `t`; height is a
    constant-gravity parabola, so the object hangs at the top and is fastest
    at the ends. Returns (x, y)."""
    t = vb.clamp01(t)
    peak = min(peak, y0, y1)
    ra, rb = math.sqrt(y0 - peak), math.sqrt(y1 - peak)
    if ra + rb == 0:
        return x0 + (x1 - x0) * t, peak
    top = ra / (ra + rb)  # when it reaches the peak
    return x0 + (x1 - x0) * t, peak + (ra + rb) ** 2 * (t - top) ** 2


def projectile_path(x0, y0, x1, y1, peak, n=48):
    """`n` points along the whole flight, evenly spaced in time: the arc to
    draw as a guide or trail (e.g. with `vb.paths.draw`)."""
    return [projectile_arc(x0, y0, x1, y1, peak, i / (n - 1)) for i in range(n)]


def draw(n, cv):
    r, ground = 34, demo.H - 150
    x0, x1, y0, peak = 300, demo.W - 300, ground - r, 230
    t = demo.phase(n, 0.4, 2.2)
    x, y = projectile_arc(x0, y0, x1, y0, peak, t)
    height = (y0 - y) / (y0 - peak)  # 1 at the top: the shadow spreads and fades as it rises
    cv.ctx.save()
    cv.ctx.translate(x, ground + 6)
    cv.ctx.scale(1, 0.22)
    demo.dot(cv, 0, 0, r * (1.2 - 0.5 * height), color='#000000', alpha=0.45 - 0.3 * height)
    cv.ctx.restore()
    demo.floor(cv, ground)
    for i in range(int(t * 30) + 1):  # a dotted trail, one dot per equal slice of time
        px, py = projectile_arc(x0, y0, x1, y0, peak, i / 30)
        demo.dot(cv, px, py, 5, color=demo.MUTED, alpha=0.7)
    demo.dot(cv, x, y, r)
    cv.mark('ball', x - r, y - r, 2 * r, 2 * r)


TECHNIQUE = Technique(
    id='projectile-arc',
    name='Projectile Arc',
    family='principles',
    group='Physics',
    aliases=('parabolic trajectory', 'ballistic path', 'throw arc'),
    definition='An object tossed across the frame rises, slows and hangs at the top, then drops faster '
               'and faster, tracing a parabola from where it left to where it lands.',
    phrasings=('throw the ball across the screen in a nice arc',
               'lob it over like it is being tossed',
               'make it fly up and come down with real gravity'),
    related=('flight-arc', 'arcs', 'arc-bend-morph', 'electric-arc', 'bend-deformer', 'fountain'),
    api=('videobuilder.techniques.principles.projectile_arc.projectile_arc',
         'videobuilder.techniques.principles.projectile_arc.projectile_path'),
    demo=lambda: demo.film(draw),
)
