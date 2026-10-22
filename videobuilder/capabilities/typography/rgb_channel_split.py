"""RGB Channel Split: the red, green and blue parts of a word slide apart
sideways, so each letter grows coloured fringes, then snap back to white."""
import math
import random

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

CHANNELS = ((1, 0, 0), (0, 1, 0), (0, 0, 1))


def channel_split(cv, draw, offset, dy=0.0, alpha=1.0):
    """Draw `draw(cv)` as three additive copies in pure red, green and blue,
    red shifted by (-offset, -dy), green in place, blue by (+offset, +dy).
    Where all three overlap the subject reads white; where they part it
    leaves red, green, blue, cyan, magenta and yellow fringes. Only the
    shape of what `draw` paints counts (its alpha), not its colour. With
    `offset` and `dy` at 0 it is the subject in plain white."""
    c = cv.ctx
    c.push_group()
    draw(cv)
    shape = c.pop_group()
    c.push_group()
    c.set_operator(cairo.OPERATOR_ADD)
    for k, rgb in zip((-1, 0, 1), CHANNELS):
        c.save()
        c.translate(k * offset, k * dy)
        c.set_source_rgb(*rgb)
        c.mask(shape)
        c.restore()
    c.pop_group_to_source()
    c.paint_with_alpha(alpha)


def draw_split_text(cv, text, font, cx, cy, offset, dy=0.0):
    """`text` on one line centred at (cx, cy), channel-split by `offset`
    (see `channel_split`). Returns the Box of the unsplit line."""
    w, h = vb.text.block_size([text], font)
    channel_split(cv, lambda c: vb.text.draw(c, [text], font, cx - w / 2, cy - h / 2, '#ffffff'), offset, dy)
    return vb.Box(cx - w / 2, cy - h / 2, w, h)


def glitch_offset(t, peak=36.0, rest=3.0, start=0.8, end=2.2, seed=0, steps=14):
    """A ready-made split amount for second `t`: a small `rest` split, a burst
    rising to about `peak` between `start` and `end` that jumps in `steps`
    random hops per second, then back to `rest`."""
    if t <= start or t >= end:
        return rest
    env = math.sin(math.pi * (t - start) / (end - start))
    hop = random.Random(f'{seed}:{int(t * steps)}').uniform(0.45, 1.0)
    return rest + (peak - rest) * env * hop


def draw(n, cv):
    t = n / demo.FPS
    box = draw_split_text(cv, 'MOTION', demo.font(150, 800), demo.W / 2, demo.H / 2, glitch_offset(t, seed=3))
    cv.mark('text', *box)


TECHNIQUE = Technique(
    id='rgb-channel-split',
    name='RGB channel split',
    family='typography',
    group='Glitch and distortion',
    aliases=('chromatic split text', 'color fringe text', 'RGB split text'),
    definition='A word is pulled apart into its red, green and blue copies, which drift sideways '
               'so the letters show rainbow edges before lining back up into white.',
    phrasings=('make the title glitch into red and blue edges',
               'the colours of the text slide apart like a broken screen',
               'give the letters a chromatic aberration wobble'),
    related=('rgb-split', 'chromatic-dispersion', 'channel-shuffle', 'hue-cycle-fill',
             'infrared-false-color', 'sepia-tone'),
    api=('videobuilder.techniques.typography.rgb_channel_split.channel_split',
         'videobuilder.techniques.typography.rgb_channel_split.draw_split_text',
         'videobuilder.techniques.typography.rgb_channel_split.glitch_offset'),
    demo=lambda: demo.film(draw),
)
