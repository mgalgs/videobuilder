"""Kinetic poster layout: big blocks of type arrive one after another, each
sliding, scaling or turning into its own slot, until together they lock into
a composed poster."""
import math
from dataclasses import dataclass
from functools import lru_cache

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

ENTRANCES = ('left', 'right', 'up', 'down', 'scale', 'rotate')


@dataclass(frozen=True)
class PosterBlock:
    """One block of the poster: `text` centred at (`cx`, `cy`) when it has
    landed, turned `angle` radians (-pi/2 reads bottom to top). `enter` is
    how it arrives (one of `ENTRANCES`), from `start` seconds for `length`."""
    text: str
    cx: float
    cy: float
    size: float = 120
    color: object = demo.INK
    weight: int = 800
    angle: float = 0.0
    enter: str = 'left'
    start: float = 0.0
    length: float = 0.6


def draw_block(cv, block, p, font=None):
    """Draw `block` at entrance progress `p` (0 -> 1, eased here). Slides
    travel in from off the frame's edge, `scale` grows from nothing with a
    small overshoot, `rotate` swings a quarter turn into its angle. Returns
    the Box the block occupies once landed (ignoring `angle`)."""
    if block.enter not in ENTRANCES:
        raise ValueError(f'enter must be one of {", ".join(ENTRANCES)}, not {block.enter!r}')
    f = font or demo.font(block.size, block.weight)
    w, h = vb.text.block_size([block.text], f)
    p = vb.clamp01(p)
    if p <= 0:
        return vb.Box(block.cx - w / 2, block.cy - h / 2, w, h)
    e = vb.ease_out_quint(p)
    dx = dy = 0.0
    scale, angle = 1.0, block.angle
    W, H = cv.width, cv.height
    if block.enter == 'left':
        dx = -(block.cx + w) * (1 - e)
    elif block.enter == 'right':
        dx = (W - block.cx + w) * (1 - e)
    elif block.enter == 'up':
        dy = (H - block.cy + h) * (1 - e)
    elif block.enter == 'down':
        dy = -(block.cy + h) * (1 - e)
    elif block.enter == 'scale':
        scale = max(vb.ease_out_back(p), 0.0)
    else:  # rotate
        angle = block.angle - (math.pi / 2) * (1 - e)
        scale = 0.6 + 0.4 * e
    c = cv.ctx
    c.save()
    c.translate(block.cx + dx, block.cy + dy)
    c.rotate(angle)
    c.scale(scale, scale)
    vb.text.draw(cv, [block.text], f, -w / 2, -h / 2, block.color, alpha=min(1.0, p * 4))
    c.restore()
    return vb.Box(block.cx - w / 2, block.cy - h / 2, w, h)


def draw_poster(cv, blocks, t):
    """Draw every block of a poster at time `t` seconds, each at its own
    entrance progress; blocks not yet started are left out."""
    for b in blocks:
        p = vb.clamp01((t - b.start) / b.length)
        if p > 0:
            draw_block(cv, b, p)


def _left(text, x, size, weight=800, **kw):
    """A block whose landed left edge sits on the grid line `x`."""
    w, _ = vb.text.block_size([text], demo.font(size, weight))
    return lambda cy, **more: PosterBlock(text, x + w / 2, cy, size=size, weight=weight, **kw, **more)


GRID = 250  # the right column's left edge; the turned word stands in the gutter before it


@lru_cache(maxsize=None)
def _blocks():
    # Built on the first frame: placing a block on the grid measures its text.
    return (
        _left('SAY IT', GRID, 104)(118, enter='left', start=0.15),
        _left('LOUDER', GRID, 104)(222, enter='right', start=0.45),
        PosterBlock('TYPE', 165, 300, size=92, color=demo.ACCENT, angle=-math.pi / 2, enter='rotate', start=0.8),
        _left('IN MOTION', GRID, 58, color=demo.TEAL)(318, enter='up', start=1.1),
        _left('ON THE GRID', GRID, 58)(382, enter='scale', start=1.35),
        _left('VOL. 01  /  NO. 03', GRID, 20, weight=600, color=demo.MUTED)(462, enter='down', start=1.6),
    )


def draw(n, cv):
    draw_poster(cv, _blocks(), n / demo.FPS)
    if n / demo.FPS > 1.9:
        cv.mark('poster', 100, 40, demo.W - 200, demo.H - 80)


CAPABILITY = Capability(
    id='kinetic-poster-layout',
    name='Kinetic poster layout',
    family='typography',
    group='Layout and poster',
    aliases=('typographic poster motion', 'poster type animation'),
    definition='Oversized words arrive one block at a time, each sliding, scaling or turning into its '
               'slot, until together they settle into a composed poster.',
    phrasings=('big bold words fly in and build up into a poster',
               'stack the headline like a typographic poster, each piece animating into place',
               'words slide and rotate in until they form a graphic layout'),
    related=('kinetic-lyric-typography', 'layout-animation-flip', 'posterization', 'rolling-shutter-wobble',
             'headline-rotator', 'staging'),
    api=('videobuilder.capabilities.typography.kinetic_poster_layout.draw_poster',
         'videobuilder.capabilities.typography.kinetic_poster_layout.draw_block',
         'videobuilder.capabilities.typography.kinetic_poster_layout.PosterBlock'),
    demo=lambda: demo.film(draw),
)
