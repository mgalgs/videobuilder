"""Parallax letter layers: a stack of copies of one word, each at its own
depth, slides apart and back together as an imagined camera pans, the near
copies moving further than the far ones."""
import math

import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ..schema import Capability


def layer_depths(count, far=0.25):
    """`count` depths from `far` (the back copy) up to 1 (the front one),
    evenly spaced, far first -- the order to draw them in."""
    if count < 2:
        return (1.0,)
    return tuple(far + (1 - far) * i / (count - 1) for i in range(count))


def draw_letter_layers(cv, text, font, cx, cy, pan, colors, depths=None, focus=1.0, shrink=0.12):
    """Draw `text` once per entry of `colors` (far first, front last),
    centred at (cx, cy), as layers at `depths` (default: `layer_depths`).
    `pan` is the camera's (dx, dy) offset in px: a layer at depth `d` moves
    `pan * (d - focus)`, so the layer at depth `focus` holds still and the
    rest slide past it, the nearer the faster. A layer also draws smaller by
    `shrink * (1 - d)`, as far things do. Returns the Box of the front copy."""
    depths = depths or layer_depths(len(colors))
    if len(depths) != len(colors):
        raise ValueError(f'{len(colors)} colors for {len(depths)} depths')
    w, h = vb.text.block_size([text], font)
    box = None
    for d, color in zip(depths, colors):
        s = 1 - shrink * (1 - d)
        dx, dy = pan[0] * (d - focus), pan[1] * (d - focus)
        with cv.layer(dx=cx + dx, dy=cy + dy, scale=s):
            vb.text.draw(cv, [text], font, -w / 2, -h / 2, color)
        box = vb.Box(cx + dx - w * s / 2, cy + dy - h * s / 2, w * s, h * s)
    return box


COUNT = 5


def draw(n, cv):
    f = demo.font(150, 900)
    # The camera swings from up-left to down-right: the far copies trail one
    # way, cross through the front one at mid-pan, then trail the other way.
    p = vb.ease_in_out_quart(demo.phase(n, 0.2, 2.8))
    a = math.pi * (0.25 + p)
    pan = (380 * math.cos(a), 200 * math.sin(a))
    colors = [kit.mix(demo.BG, demo.TEAL, 0.25 + 0.6 * i / (COUNT - 2)) for i in range(COUNT - 1)] + [demo.INK]
    box = draw_letter_layers(cv, 'DEPTH', f, demo.W / 2, demo.H / 2, pan, colors, focus=0.9)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='parallax-letter-layers',
    name='Parallax letter layers',
    family='typography',
    group='Depth and 3D',
    aliases=('depth letter parallax', 'layered type depth', 'stacked type parallax'),
    definition='Several copies of the same word are stacked at different depths and slide at '
               'different speeds as the view shifts, so the word seems to have layers behind it.',
    phrasings=('repeat the title a few times behind itself and let the copies drift apart in 3D',
               'a stack of echo words that separate with parallax when the camera moves',
               'layered copies of the text that move at different speeds to show depth'),
    related=('parallax-layers', 'pointer-parallax-layers', 'parallax-slide', 'scroll-parallax-layers',
             'two-point-five-d-photo-parallax', 'layered-fog-bands'),
    api=('videobuilder.capabilities.typography.parallax_letter_layers.draw_letter_layers',
         'videobuilder.capabilities.typography.parallax_letter_layers.layer_depths'),
    demo=lambda: demo.film(draw),
)
