"""RGB Split: the picture's red, green and blue channels slide apart
sideways, the scene swaps while they are furthest apart, then they slide
back together on the incoming scene."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

CHANNELS = ((1, 0, 0), (0, 1, 0), (0, 0, 1))


def channel_split(cv, draw, shift, dy=0.0):
    """Draw `draw(c)` onto `cv` with its colour channels pulled apart: red
    offset by `-shift` px, green left in place, blue by `+shift` (and `dy`
    vertically, red up and blue down). The channels add back to the plain
    picture where they overlap; edges smear rather than leave gaps. Usable
    on its own as a held chromatic-aberration look."""
    sub = vb.Canvas(cv.width, cv.height, scale=cv.scale, format=cv.format)
    draw(sub)
    sub.surface.flush()
    pw, ph = sub.surface.get_width(), sub.surface.get_height()
    c = cv.ctx
    c.save()
    c.identity_matrix()
    c.set_source_rgb(0, 0, 0)
    c.paint()
    for k, rgb in zip((-1, 0, 1), CHANNELS):
        part = cairo.ImageSurface(cairo.FORMAT_ARGB32, pw, ph)
        pc = cairo.Context(part)
        pc.set_source_surface(sub.surface, 0, 0)
        pc.paint()
        pc.set_operator(cairo.OPERATOR_MULTIPLY)
        pc.set_source_rgb(*rgb)
        pc.paint()
        c.set_operator(cairo.OPERATOR_ADD)
        c.set_source_surface(part, k * shift * cv.scale, k * dy * cv.scale)
        c.get_source().set_extend(cairo.EXTEND_PAD)
        c.paint()
    c.restore()


def rgb_split(cv, a, b, p, shift=90, swap=(0.42, 0.58)):
    """Draw the split at progress `p` (0 -> 1): `a(cv)`'s channels part
    sideways up to `shift` px, the scene cross-fades to `b(cv)` across the
    `swap` window while they are furthest apart, then they close up on `b`.

    In a film, call it while two shots are live in an overlap, e.g.
    `rgb_split(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    t = vb.clamp01((p - swap[0]) / (swap[1] - swap[0]))
    t = t * t * (3 - 2 * t)

    def scene(c):
        if t < 1:
            a(c)
        if t > 0:
            with c.layer(opacity=t):
                b(c)

    amount = math.sin(math.pi * p) ** 2
    channel_split(cv, scene, shift * amount, dy=shift * 0.12 * amount)


TECHNIQUE = Technique(
    id='rgb-split',
    name='RGB split',
    family='transitions',
    group='Glitch',
    aliases=('chromatic aberration transition', 'colour split', 'channel split', 'chromatic aberration',
             'colour fringing'),
    definition='The red, green and blue layers of the picture drift apart sideways into coloured ghosts, '
               'the shot changes under them, and they snap back together on the new scene.',
    phrasings=('glitch to the next shot with the colours separating',
               'pull the colour channels apart and bring them back on scene two',
               'a chromatic aberration cut between the scenes'),
    related=('rgb-channel-split', 'chromatic-dispersion', 'channel-shuffle', 'palette-shift-transition',
             'cross-processing', 'split-screen-transition'),
    api=('videobuilder.techniques.transitions.rgb_split.rgb_split',
         'videobuilder.techniques.transitions.rgb_split.channel_split'),
    demo=lambda: demo.two_scenes(rgb_split),
)
