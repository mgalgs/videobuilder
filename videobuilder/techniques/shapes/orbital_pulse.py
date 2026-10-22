"""Orbital Pulse: a dot circles a dim ring, and the stretch of ring it has
just crossed lights up behind it, fading out with distance like a comet's
tail."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def draw_orbital_pulse(cv, cx, cy, r, turns, color, track=None, trail=0.5, width=6, dot_r=None,
                       start=-math.pi / 2, glow=True, steps=48):
    """Draw a ring of radius `r` centred at (cx, cy) with a dot `turns` of the
    way around it (0 -> 1 is one lap clockwise from `start`, 12 o'clock by
    default; values past 1 keep circling). The ring itself is `track` (default
    `color` at low strength); behind the dot the stroke brightens to `color`
    over `trail` of a lap, fading to nothing at its tail. The lit stretch never
    reaches further back than where the dot set off. `steps` is how many
    pieces the fade is drawn in. Returns the dot's centre (x, y)."""
    dot_r = width * 1.9 if dot_r is None else dot_r
    if track is None:
        cv.arc(cx, cy, r, 0, 2 * math.pi, color, width=width, alpha=0.18)
    else:
        cv.arc(cx, cy, r, 0, 2 * math.pi, track, width=width)
    head = start + 2 * math.pi * turns
    span = 2 * math.pi * min(trail, max(turns, 0.0))
    if span > 0:
        seg = span / steps
        for i in range(steps):  # tail first, so the brighter pieces lie on top
            a0 = head - span + i * seg
            cv.arc(cx, cy, r, a0, a0 + seg * 1.05, color, width=width, alpha=((i + 1) / steps) ** 1.6)
    x, y = cx + r * math.cos(head), cy + r * math.sin(head)
    if glow:
        for k, a in ((2.6, 0.08), (1.9, 0.14), (1.4, 0.25)):
            demo.dot(cv, x, y, r=dot_r * k, color=color, alpha=a)
    demo.dot(cv, x, y, r=dot_r, color=color)
    return x, y


_EASE = vb.bezier(0.37, 0, 0.63, 1)  # a gentle in-out, so the orbit reads as steady


def draw(n, cv):
    cx, cy, r = demo.W / 2, demo.H / 2, demo.H * 0.32
    turns = 1.6 * _EASE(demo.phase(n, 0.2, 2.9))
    x, y = draw_orbital_pulse(cv, cx, cy, r, turns, demo.ACCENT, trail=0.55, width=5)
    cv.mark('dot', x - 10, y - 10, 20, 20)


TECHNIQUE = Technique(
    id='orbital-pulse',
    name='Orbital pulse',
    family='shapes',
    group='Geometric motion',
    aliases=('ring pulse orbit', 'orbiting pulse dot', 'halo ring orbit'),
    definition='A glowing dot circles a faint ring, and the part of the ring it has just passed '
               'lights up behind it and fades away like a tail.',
    phrasings=('a dot running around a circle that leaves a glowing trail on the ring',
               'make the ring light up behind a point as it orbits',
               'a little light chasing around a circular track'),
    related=('orbit', 'orbit-loader', 'pulse-loader', 'location-ripple-pulse', 'radial-stagger',
             'highlight-circle-draw'),
    api=('videobuilder.techniques.shapes.orbital_pulse.draw_orbital_pulse',),
    demo=lambda: demo.film(draw),
)
