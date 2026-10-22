"""Orbit Loader: a busy indicator made of a few small dots circling a still
centre on one shared ring, each at its own steady speed, so they keep
passing and lapping one another while something loads."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def orbit_positions(cx, cy, t, r=60, speeds=(1 / 3, 2 / 3, 1.0), starts=None):
    """Where each dot is at time `t` seconds: a list of `(x, y, angle)`.
    Dot `i` turns clockwise at `speeds[i]` turns per second from angle
    `starts[i]` (radians, 0 = 12 o'clock; default: spread evenly round the
    ring). For a seamless loop of `L` seconds, give speeds that are whole
    multiples of `1 / L` (the defaults loop every 3 s)."""
    starts = starts if starts is not None else [2 * math.pi * i / len(speeds) for i in range(len(speeds))]
    out = []
    for s, a0 in zip(speeds, starts):
        a = a0 + 2 * math.pi * s * t - math.pi / 2
        out.append((cx + r * math.cos(a), cy + r * math.sin(a), a))
    return out


def draw_orbit_loader(cv, cx, cy, t, r=60, dot=9, speeds=(1 / 3, 2 / 3, 1.0), starts=None,
                      colors=(demo.ACCENT, demo.TEAL, demo.TEAL), sizes=None, hub=demo.INK,
                      track=demo.LINE, trail=0.2, alpha=1.0):
    """Draw an orbit loader centred at (cx, cy) at time `t` seconds: a faint
    `track` ring of radius `r`, a small `hub` dot at the centre, and one dot
    per entry of `speeds` going round it (see `orbit_positions`). `colors`
    and `sizes` (radius multipliers on `dot`) cycle per dot. `trail` is the
    length in turns of each dot's fading wake, scaled by its speed (0 for
    none). `hub` or `track` of None leaves it out. Returns the Box it fills."""
    with cv.layer(opacity=alpha):
        if track:
            cv.arc(cx, cy, r, 0, 2 * math.pi, track, width=max(1.5, dot * 0.22))
        if hub:
            demo.dot(cv, cx, cy, dot * 0.75, color=hub)
        sizes = sizes or [1.4 if i == 0 else 1.0 for i in range(len(speeds))]
        dots = orbit_positions(cx, cy, t, r, speeds, starts)
        for i, ((x, y, a), s) in enumerate(zip(dots, speeds)):
            color, size = colors[i % len(colors)], dot * sizes[i % len(sizes)]
            if trail > 0:
                sweep = 2 * math.pi * trail * min(1.0, s)
                steps = 24
                for k in range(steps, 0, -1):
                    b = a - sweep * k / steps
                    f = 1 - k / steps
                    demo.dot(cv, cx + r * math.cos(b), cy + r * math.sin(b), size * (0.35 + 0.55 * f),
                             color=color, alpha=0.18 * f)
            demo.dot(cv, x, y, size, color=color)
    pad = dot * 1.6
    return vb.Box(cx - r - pad, cy - r - pad, 2 * (r + pad), 2 * (r + pad))


def draw(n, cv):
    cx, cy = demo.W / 2, demo.H / 2 - 30
    box = draw_orbit_loader(cv, cx, cy, n / demo.FPS, r=150, dot=20)
    cv.mark('loader', *box)
    demo.word(cv, 'Loading', cx, cy + 250, size=40, color=demo.MUTED, weight=600)


TECHNIQUE = Technique(
    id='orbit-loader',
    name='Orbit loader',
    family='ui',
    group='Loaders',
    aliases=('orbiting dots', 'planet loader', 'orbit spinner'),
    definition='A waiting indicator where a few small dots circle a still centre point on the same ring, '
               'each at its own constant speed, so they keep overtaking one another.',
    phrasings=('a loading spinner with little dots going round in a circle',
               'dots orbiting a centre point while it loads',
               'a planet-style loader with moons circling at different speeds'),
    related=('orbital-pulse', 'orbit', 'orbiting-characters', 'two-body-orbit', 'orbit-shot', 'circle-pop'),
    api=('videobuilder.techniques.ui.orbit_loader.draw_orbit_loader',
         'videobuilder.techniques.ui.orbit_loader.orbit_positions'),
    demo=lambda: demo.film(draw),
)
