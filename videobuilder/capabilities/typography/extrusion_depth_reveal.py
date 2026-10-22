"""Extrusion Depth Reveal: flat type grows a solid side, the depth pushing
out from behind each letter until the word stands as a block."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def _shade(color, k):
    """`color` darkened towards black by `k` (0 -> 1), as an (r, g, b) tuple."""
    r, g, b, _ = vb.rgba(color)
    return tuple(round(c * 255 * (1 - k)) for c in (r, g, b))


def draw_extruded(cv, text, font, x, y, depth, color, side, angle=45.0, shade=0.45, step=1.0):
    """Draw `text` from its top-left (x, y) as extruded type: the face in
    `color`, with a solid side `depth` px deep running away at `angle` degrees
    (0 is to the right, 90 straight down), in `side`, darkening by up to
    `shade` towards the back. Animate `depth` from 0 to reveal it. The side is
    stacked copies `step` px apart, so the face never moves. Returns the Box
    of the face."""
    dx, dy = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    slices = math.ceil(max(0.0, depth) / step)
    for i in range(slices, 0, -1):
        d = min(i * step, depth)
        vb.text.draw(cv, [text], font, x + dx * d, y + dy * d, _shade(side, shade * d / max(depth, 1e-9)))
    return vb.text.draw(cv, [text], font, x, y, color)


def depth_at(p, depth, ease=vb.ease_out_quint):
    """The extrusion depth at progress `p` (0 -> 1): eased from 0 to `depth`."""
    return depth * ease(vb.clamp01(p))


DEPTH = 80
ANGLE = 50


def draw(n, cv):
    f = demo.font(190, 900)
    text = 'DEPTH'
    w, h = vb.text.block_size([text], f)
    # centre the finished block, face plus its full side
    x = (demo.W - w - DEPTH * math.cos(math.radians(ANGLE))) / 2
    y = (demo.H - h - DEPTH * math.sin(math.radians(ANGLE))) / 2
    d = depth_at(demo.phase(n, 0.4, 2.4), DEPTH, ease=vb.ease_in_out_quart)
    box = draw_extruded(cv, text, f, x, y, d, demo.INK, demo.TEAL, angle=ANGLE)
    cv.mark('text', *box)


TECHNIQUE = Technique(
    id='extrusion-depth-reveal',
    name='Extrusion depth reveal',
    family='typography',
    group='Depth and 3D',
    aliases=('3D extruded type', 'extrude in', 'growing extrusion'),
    definition='Flat lettering sprouts a solid side that pushes out behind each glyph until the word '
               'reads as a thick three-dimensional block.',
    phrasings=('make the title go from flat to chunky 3D letters',
               'the words grow a thick side so they look like solid blocks',
               'extrude the headline out so it gains depth over a couple of seconds'),
    related=('extrusion', 'x-ray-view', 'text-mask-reveal', 'character-rise', 'typewriter-reveal',
             'long-shadow-growth'),
    api=('videobuilder.techniques.typography.extrusion_depth_reveal.draw_extruded',
         'videobuilder.techniques.typography.extrusion_depth_reveal.depth_at'),
    demo=lambda: demo.film(draw),
)
