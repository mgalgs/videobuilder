"""Volume Preservation: when a shape squashes or stretches along one axis it
gives the amount back on the other, so it never looks like it grew or shrank,
only that it changed shape."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def preserve_volume(stretch, dims=2):
    """A stretch along y (1 = rest, 1.4 = tall and thin, 0.7 = squashed) ->
    the `(sx, sy)` scale that keeps the shape's size. `dims=2` keeps its area
    on screen (sx = 1 / stretch); `dims=3` treats it as a solid whose depth
    narrows too, so the width gives back less (sx = 1 / sqrt(stretch))."""
    if stretch <= 0:
        raise ValueError(f'stretch must be positive, not {stretch!r}')
    if dims not in (2, 3):
        raise ValueError(f'dims must be 2 or 3, not {dims!r}')
    return (1 / stretch if dims == 2 else 1 / math.sqrt(stretch)), stretch


def _stretch(t):
    """The demo's stretch over time: tall, then flattened, then a wobble that dies away."""
    return vb.interpolate(t, (0.0, 0.35, 0.8, 1.25, 1.65, 2.0, 2.35, 2.7, 3.0),
                          (1.0, 1.0, 1.55, 0.6, 1.3, 0.82, 1.08, 1.0, 1.0),
                          ease=lambda x: 0.5 - 0.5 * math.cos(math.pi * x))


def draw(n, cv):
    r, ground, cx = 72, demo.H - 110, demo.W / 2
    sx, sy = preserve_volume(_stretch(n / demo.FPS))
    w, h = r * sx, r * sy
    demo.floor(cv, ground)
    cv.arc(cx, ground - r, r, 0, 2 * math.pi, demo.MUTED, width=3, alpha=0.45)  # the shape at rest
    cv.ctx.save()
    cv.ctx.translate(cx, ground - h)   # sits on the floor: grows up from it, spreads along it
    cv.ctx.scale(sx, sy)
    demo.dot(cv, 0, 0, r)
    cv.ctx.restore()
    cv.mark('blob', cx - w, ground - 2 * h, 2 * w, 2 * h)
    demo.word(cv, f'width {sx:.2f}  ×  height {sy:.2f}  =  1.00', cx, 64, size=28,
              color=demo.INK, font=demo.mono(28))


TECHNIQUE = Technique(
    id='volume-preservation',
    name='Volume Preservation',
    family='principles',
    group='Principle sub-techniques',
    aliases=('constant volume', 'area preservation', 'mass conservation'),
    definition='A shape that gets thinner as it stretches and wider as it squashes, so its overall size '
               'stays the same while its proportions change.',
    phrasings=('squash it without making it look bigger or smaller',
               'when it stretches tall it should get skinnier',
               'keep the ball the same amount of stuff as it deforms'),
    related=('squash-and-stretch', 'circle-packing', 'extrusion', 'solid-drawing', 'wobble', 'morphing-blob'),
    api=('videobuilder.techniques.principles.volume_preservation.preserve_volume',),
    demo=lambda: demo.film(draw),
)
