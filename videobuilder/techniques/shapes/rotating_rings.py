"""Rotating Rings: a stack of concentric rings, each turning at its own speed
and in its own direction; breaks and dashes in the strokes are what let the
eye see them turn."""
import math
from dataclasses import dataclass

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

TAU = 2 * math.pi


@dataclass(frozen=True)
class Ring:
    """One ring of a `rotating_rings` stack. `radius` in px; `speed` in turns
    per second, negative turns anticlockwise. `arcs` are `(start, length)`
    pairs in fractions of a turn, the parts of the circle that are drawn
    (default: one arc with a quarter missing); `dash` is `(on, off)` in px to
    draw the arcs dashed instead of solid. `track` is the alpha of a faint
    full circle drawn under the arcs (0 for none)."""
    radius: float
    speed: float
    color: object = demo.INK
    width: float = 6
    arcs: tuple = ((0.0, 0.75),)
    dash: tuple = None
    track: float = 0.0
    phase: float = 0.0


def draw_ring(cv, cx, cy, ring, turn, alpha=1.0, round_caps=True):
    """Draw `ring` centred at (cx, cy), rotated by `turn` (fractions of a
    turn, clockwise on screen) on top of its own `phase`."""
    ctx = cv.ctx
    if ring.track > 0:
        cv.arc(cx, cy, ring.radius, 0, TAU, ring.color, width=max(1, ring.width * 0.35),
               alpha=ring.track * alpha)
    ctx.save()
    ctx.set_line_cap(1 if round_caps and not ring.dash else 0)
    if ring.dash:
        ctx.set_dash(list(ring.dash))
    base = (turn + ring.phase) * TAU - math.pi / 2  # 0 is twelve o'clock
    for start, length in ring.arcs:
        a0 = base + start * TAU
        cv.arc(cx, cy, ring.radius, a0, a0 + length * TAU, ring.color, width=ring.width, alpha=alpha)
    ctx.restore()


def rotating_rings(cv, cx, cy, t, rings, alpha=1.0, spin=1.0):
    """Draw every `Ring` in `rings` centred at (cx, cy) at time `t` seconds,
    each turned by its own `speed * t`. `spin` scales every speed at once
    (ease it from 0 to 1 to spin the stack up). Returns the bounding Box."""
    for ring in rings:
        draw_ring(cv, cx, cy, ring, ring.speed * t * spin, alpha=alpha)
    r = max((g.radius + g.width / 2 for g in rings), default=0)
    return vb.Box(cx - r, cy - r, 2 * r, 2 * r)


RINGS = (
    Ring(215, 0.10, demo.MUTED, width=3, arcs=((0.0, 1.0),), dash=(16, 13)),
    Ring(178, -0.22, demo.ACCENT, width=6, arcs=((0.0, 0.62),), track=0.12),
    Ring(138, 0.32, demo.INK, width=4.5, arcs=((0.0, 0.3), (0.42, 0.22), (0.72, 0.18)), track=0.10),
    Ring(96, -0.45, demo.TEAL, width=7, arcs=((0.0, 0.8),), track=0.12),
    Ring(58, 0.7, demo.MUTED, width=2.5, arcs=((0.0, 1.0),), dash=(6, 8)),
)


def draw(n, cv):
    box = rotating_rings(cv, demo.W / 2, demo.H / 2, n / demo.FPS, RINGS)
    cv.mark('rings', *box)


TECHNIQUE = Technique(
    id='rotating-rings',
    name='Rotating rings',
    family='shapes',
    group='Geometric motion',
    aliases=('concentric ring spin', 'spinning ring loader', 'orbiting rings'),
    definition='Nested circles share one centre and each turns at its own pace, some one way and some '
               'the other, with broken or dashed strokes so the turning is easy to follow.',
    phrasings=('a few circles inside each other all spinning at different speeds',
               'layered rings turning in opposite directions, like a sci-fi loader',
               'concentric dashed circles slowly rotating around the middle'),
    related=('spinner-ring', 'ripple-rings', 'rotating-circular-text', 'progress-ring', 'radial-stagger', 'spin'),
    api=('videobuilder.techniques.shapes.rotating_rings.rotating_rings',
         'videobuilder.techniques.shapes.rotating_rings.Ring',
         'videobuilder.techniques.shapes.rotating_rings.draw_ring'),
    demo=lambda: demo.film(draw),
)
