"""Elastic Stretch: the outgoing scene is pulled out like taffy toward the way
it is leaving, necking thinner where it stretches most, then lets go and
snaps away, and the incoming scene underneath gives a small elastic wobble."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

AXES = {'left': (0, -1), 'right': (0, 1), 'up': (1, -1), 'down': (1, 1)}


def _stretched(cv, scene, s, shift, axis, sign, strips):
    """Draw `scene` resampled in `strips` slices along `axis`, its trailing
    edge moved `shift` px toward the exit. A slice's stretch along the axis
    grows with its distance from the trailing edge (`1 + 2 s` at the leading
    edge) and it thins across the axis to keep its area, so the leading side
    is the longest and thinnest."""
    W, H = cv.width, cv.height
    L = W if axis == 0 else H

    def at(u):  # u: 0 at the leading edge, 1 at the trailing edge -> position on the axis
        back = L * (1 - u) * (1 + s * (1 - u))
        return L - shift - back if sign < 0 else shift + back

    def thin(u):  # across-axis scale that keeps the slice's area
        return 1 / math.sqrt(1 + 2 * s * (1 - u))

    c = cv.ctx
    for i in range(strips):
        u0, u1 = i / strips, (i + 1) / strips
        p0, p1 = at(u0), at(u1)
        a0, a1 = (u0 * L, u1 * L) if sign < 0 else ((1 - u0) * L, (1 - u1) * L)  # where the slice sits in `scene`
        if max(p0, p1) < 0 or min(p0, p1) > L:
            continue
        # the clip runs half a slice on into the next one, which paints over it, so no seam shows
        u2 = min(1.0, u1 + 0.5 / strips)
        quad = [(p0, -thin(u0)), (at(u2), -thin(u2)), (at(u2), thin(u2)), (p0, thin(u0))]  # (along, across)
        c.save()
        c.new_path()
        for x, y in quad:
            if axis == 0:
                c.line_to(x, H / 2 + H * y / 2)
            else:
                c.line_to(W / 2 + W * y / 2, x)
        c.close_path()
        c.clip()
        k = thin((u0 + u1) / 2)
        g = (p1 - p0) / (a1 - a0)
        if axis == 0:
            c.translate(p0, H / 2)
            c.scale(g, k)
            c.translate(-a0, -H / 2)
        else:
            c.translate(W / 2, p0)
            c.scale(k, g)
            c.translate(-W / 2, -a0)
        scene(cv)
        c.restore()


def elastic_stretch(cv, a, b, p, direction='left', stretch=0.7, release=0.5, strips=40):
    """Draw the elastic stretch at progress `p` (0 -> 1).

    Until `release`, `a(cv)` is pulled toward `direction` ('left', 'right',
    'up' or 'down') with its trailing edge pinned: it lengthens by up to
    `stretch` (0.7 = 70 % more at the leading side, scaled up from there) and
    pinches thinner, showing `b(cv)` around it. Then it lets go: the trailing
    edge whips out of frame while the band shortens back, and `b` recoils in a
    small damped wobble. `strips` is how finely `a` is resampled.

    In a film, call it while both shots are live in an overlap, e.g.
    `elastic_stretch(cv, lambda c: shot_a(c, old), lambda c: shot_b(c, new), new.f / overlap_frames)`."""
    axis, sign = AXES[direction]
    L = cv.width if axis == 0 else cv.height
    p = vb.clamp01(p)
    if p < release:
        t = p / release
        s, shift = stretch * t * t * (3 - 2 * t), 0.0     # pull slowly, then hold taut
    else:
        q = (p - release) / (1 - release)
        s = stretch * (1 - q) ** 2
        shift = L * 2.2 * q * q                        # the pinned edge lets go and races out
    wob = 0.0
    if p > release:  # b recoils as the band lets go, three damped swings
        q = (p - release) / (1 - release)
        wob = 0.035 * math.exp(-4 * q) * math.sin(q * 3 * 2 * math.pi)
    c = cv.ctx
    c.save()
    if axis == 0:
        c.translate(sign * wob * cv.width, 0)
    else:
        c.translate(0, sign * wob * cv.height)
    b(cv)
    c.restore()
    _stretched(cv, a, s, shift, axis, sign, strips)


CAPABILITY = Capability(
    id='elastic-stretch',
    name='Elastic stretch',
    family='transitions',
    group='Organic and Fluid',
    aliases=('rubber band transition', 'stretch snap', 'taffy pull'),
    definition='The old scene is tugged out like a rubber band, growing long and thin toward one side, '
               'then lets go and whips off, leaving the new scene wobbling into place.',
    phrasings=('pull the first shot out like rubber until it snaps away',
               'stretch the old scene sideways and let it twang off to show the next one',
               'a gooey stretchy wipe to the next scene'),
    related=('rubber-band-snap', 'rubber-band-overscroll', 'elastic-ease-out', 'elastic-ease-in',
             'squash-on-tap', 'crumple'),
    api=('videobuilder.capabilities.transitions.elastic_stretch.elastic_stretch',),
    demo=lambda: demo.two_scenes(elastic_stretch, start=0.6, length=1.8),
)
