"""Gooey Filter: plain circles blurred together and cut at a threshold, so
they fuse into one liquid blob wherever they near each other. videobuilder
already has the blur-then-threshold pass as `goo` (written for metaball
text), so this entry only names it and demos it on loose dots."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ..typography.metaball_goo_text import goo

# (orbit radius when spread, angle offset, dot radius)
DOTS = ((165, 0.0, 34), (165, math.pi / 2, 34), (165, math.pi, 34), (165, 3 * math.pi / 2, 34),
        (95, math.pi / 4, 22), (95, 5 * math.pi / 4, 22))


def draw(n, cv):
    t = n / demo.FPS
    # Spread out, then swirl inward until they pool into one blob, then
    # start pulling apart again so the necks stretch and snap.
    gather = vb.ease_in_out_quart(demo.phase(n, 0.2, 1.9)) - 0.4 * vb.ease_in_out_quart(demo.phase(n, 2.2, 3.0))
    spin = 0.6 * t
    cx, cy = demo.W / 2, demo.H / 2
    pts = []
    for i, (rad, a0, r) in enumerate(DOTS):
        d = rad * (1 - 0.8 * gather) + 10 * math.sin(2.2 * t + i * 1.3)
        a = a0 + spin * (1 if i < 4 else -1.4)
        pts.append((cx + d * math.cos(a), cy + d * math.sin(a), r))

    def shapes(sub):
        for x, y, r in pts:
            demo.dot(sub, x, y, r, color='#ffffff')
    pad = 250
    goo(cv, shapes, demo.ACCENT, blur=22, cut=0.5, box=(cx - pad, cy - pad, 2 * pad, 2 * pad))
    cv.mark('blob', cx - pad, cy - pad, 2 * pad, 2 * pad)


TECHNIQUE = Technique(
    id='gooey-filter',
    name='Gooey filter',
    family='particles',
    group='Metaballs & blobs',
    aliases=('goo effect', 'goo filter', 'gooey threshold', 'SVG goo', 'gooey blob', 'blur and threshold'),
    definition='Separate round dots are softened and then cut back to a hard edge, so whenever two '
               'come close they melt into a single liquid shape joined by a stretchy neck.',
    phrasings=('make the dots blobby so they merge like liquid when they touch',
               'circles that pool together into one goopy blob and pull apart again',
               'that sticky lava-lamp look where bubbles fuse as they drift past each other'),
    related=('zoom-blur', 'gaussian-blur', 'spin-blur', 'ripple', 'refraction-ripple', 'blur-dissolve'),
    api=('videobuilder.techniques.typography.metaball_goo_text.goo',),
    demo=lambda: demo.film(draw),
)
