"""Kaleidoscope: the outgoing scene folds into mirrored wedges around the
centre, the pattern spins and swaps to the incoming scene, then unfolds."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _ramp(x):
    x = vb.clamp01(x)
    return x * x * (3 - 2 * x)


def mirror_wedges(cv, draw, segments=8, turn=0.0, zoom=1.0, cx=None, cy=None, alpha=1.0):
    """Paint whatever `draw(cv)` paints as a kaleidoscope: one wedge of it
    (2*pi/`segments` wide, at the centre (cx, cy), default the frame's)
    repeated round the centre, every other copy mirrored so neighbours meet
    edge to edge. `turn` spins the pattern (radians); `zoom` magnifies the
    sampled wedge. `segments` should be even so the last seam matches too.
    Marks `draw` makes are dropped: the picture is no longer where they say."""
    c = cv.ctx
    cx = cv.width / 2 if cx is None else cx
    cy = cv.height / 2 if cy is None else cy
    marks = len(cv.marks)
    c.push_group()
    draw(cv)
    src = c.pop_group()
    del cv.marks[marks:]
    src.set_extend(cairo.EXTEND_REFLECT)
    src.set_filter(cairo.FILTER_GOOD)
    seg = 2 * math.pi / segments
    reach = math.hypot(cv.width, cv.height)
    eps = 0.004  # wedges overlap a hair so no background shows through the seams
    c.save()
    c.push_group()
    for k in range(segments):
        a0 = turn + k * seg
        c.save()
        c.new_path()
        c.move_to(cx, cy)
        c.arc(cx, cy, reach, a0 - eps, a0 + seg + eps)
        c.close_path()
        c.clip()
        c.translate(cx, cy)
        if k % 2:
            c.rotate(a0 + seg)
            c.scale(1, -1)
        else:
            c.rotate(a0)
        c.scale(zoom, zoom)
        c.translate(-cx, -cy)
        c.set_source(src)
        c.paint()
        c.restore()
    c.pop_group_to_source()
    c.paint_with_alpha(alpha)
    c.restore()


def kaleidoscope(cv, a, b, p, segments=12, turns=0.5, zoom=0.6, fold=0.3):
    """Draw the kaleidoscope transition at progress `p` (0 -> 1): `a(cv)`
    folds into `segments` mirrored wedges over the first `fold` of the move,
    the pattern spins `turns` full turns and its wedge scales towards `zoom`
    (below 1 samples a wider slice, so more of the scene repeats), swaps to
    `b(cv)` mid-way, and unfolds into plain `b` over the last `fold`.

    In a film, call it inside a two-shot overlap, e.g.
    `kaleidoscope(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    p = vb.clamp01(p)
    folded = _ramp(p / fold) * _ramp((1 - p) / fold)
    swap = _ramp((p - 0.42) / 0.16)             # a vs b inside the pattern
    turn = 2 * math.pi * turns * vb.ease_in_out_quart(p)
    z = 1 + (zoom - 1) * math.sin(math.pi * p)
    (b if p >= 0.5 else a)(cv)                  # the plain scene under the fold
    if folded <= 0:
        return
    if swap < 1:
        mirror_wedges(cv, a, segments, turn, z, alpha=folded)
    if swap > 0:
        mirror_wedges(cv, b, segments, turn, z, alpha=folded * swap)


CAPABILITY = Capability(
    id='kaleidoscope',
    name='Kaleidoscope',
    family='transitions',
    group='Organic and Fluid',
    aliases=('kaleidoscope transition', 'mirror kaleidoscope', 'radial mirror', 'mandala mirror',
             'mirror fold', 'kaleidoscope tunnel'),
    definition='The shot breaks into a ring of mirror-image slices around its centre that turn like a '
               'kaleidoscope, and when the pattern settles the next shot is showing.',
    phrasings=('make the picture go all kaleidoscopic and come out on the next scene',
               'mirror the shot into a spinning mandala, then land on the new one',
               'a trippy symmetrical spin between the two clips'),
    related=('spin', 'rotoscope-look', 'lens-flare', 'tessellation-triangle-flip', 'flip', 'cube-rotate'),
    api=('videobuilder.capabilities.transitions.kaleidoscope.kaleidoscope',
         'videobuilder.capabilities.transitions.kaleidoscope.mirror_wedges'),
    demo=lambda: demo.two_scenes(kaleidoscope, start=0.6, length=1.8),
)
