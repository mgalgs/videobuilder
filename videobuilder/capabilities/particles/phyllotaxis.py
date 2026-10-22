"""Phyllotaxis: seeds are laid down one after another, each turned a golden
angle from the last and pushed out by the square root of its index, so the
head grows outward from its centre and crossing spiral arms appear on their
own, as in a sunflower."""
import math

import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ..schema import Capability

GOLDEN_ANGLE = math.pi * (3 - math.sqrt(5))  # ~137.5 degrees: the turn between consecutive seeds


def phyllotaxis(count, spacing, angle=GOLDEN_ANGLE, rotation=0.0):
    """The first `count` seeds of a phyllotaxis head as `(dx, dy)` offsets
    from its centre, oldest (innermost) first. Seed `i` sits at angle
    `i * angle + rotation` and distance `spacing * sqrt(i)`, so the seeds
    pack evenly and the head's radius grows with the square root of its
    count. Any `angle` other than the golden one shows straight spokes
    instead of spirals."""
    out = []
    for i in range(max(int(count), 0)):
        a = i * angle + rotation
        r = spacing * math.sqrt(i)
        out.append((r * math.cos(a), r * math.sin(a)))
    return out


def draw_phyllotaxis(cv, cx, cy, p, count=420, spacing=11.0, seed=5.0, colors=(demo.ACCENT, '#f2a541'), arms=21,
                     fresh=12, flash=demo.INK, angle=GOLDEN_ANGLE, rotation=0.0):
    """Draw a phyllotaxis head growing at (cx, cy): at progress `p` (0 -> 1)
    the first `p * count` seeds are placed, one at a time, at the rim. Each
    new seed pops in over the next `fresh` seeds' worth of growth, starting
    as a `flash` dot and settling into its colour; seeds swell slightly
    towards the rim. Colours cycle through `colors` by which of `arms`
    spiral arms a seed lies on (13, 21 and 34 are the arms the golden angle
    shows). Returns the head's current radius."""
    grown = vb.clamp01(p) * count
    whole = math.ceil(grown)
    for i, (dx, dy) in enumerate(phyllotaxis(whole, spacing, angle, rotation)):
        age = vb.clamp01((grown - i) / fresh)  # 0 the moment it lands, 1 once `fresh` more seeds have followed
        size = seed * (0.8 + 0.4 * math.sqrt(i / count)) * vb.ease_out_back(min(1.0, age * 3))
        if size <= 0:
            continue
        color = colors[i % arms % len(colors)]
        demo.dot(cv, cx + dx, cy + dy, size, color=kit.mix(flash, color, age) if age < 1 else color)
    return spacing * math.sqrt(max(whole - 1, 0)) + seed


def draw(n, cv):
    cx, cy = demo.W / 2, demo.H / 2
    r = draw_phyllotaxis(cv, cx, cy, demo.phase(n, 0.15, 2.6), rotation=0.12 * n / demo.FPS)
    cv.mark('head', cx - r, cy - r, 2 * r, 2 * r)


CAPABILITY = Capability(
    id='phyllotaxis',
    name='Phyllotaxis',
    family='particles',
    group='Growth & L-systems',
    aliases=('sunflower spiral', 'golden angle spiral', 'Vogel spiral', 'sunflower seed pattern'),
    definition='Dots are added one by one, each turned about 137.5 degrees from the last and set a little '
               'further out, so a round seed head grows from the centre with interlocking spiral arms.',
    phrasings=('dots filling in like the seeds of a sunflower head',
               'a golden-ratio spiral of points growing out from the middle',
               'grow a sunflower pattern one dot at a time'),
    related=('spiral-bloom', 'pie-sweep', 'spiral-galaxy', 'spiral-expansion-draw', 'radial-stagger',
             'dragon-curve'),
    api=('videobuilder.capabilities.particles.phyllotaxis.draw_phyllotaxis',
         'videobuilder.capabilities.particles.phyllotaxis.phyllotaxis'),
    demo=lambda: demo.film(draw),
)
