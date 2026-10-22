"""Logo Glitch Reveal: the logo stutters on like a broken signal -- flickering
in and out, torn into horizontal slices that jump sideways, with red and cyan
ghosts split off it -- and the damage calms until it locks clean."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

SPLIT = ('#ff2d5a', '#29e3ff')


def glitch_reveal(cv, draw_logo, box, p, seed=0, steps=24, slices=8, tear=0.22, split=16,
                  colors=SPLIT, settle=0.85):
    """Draw a logo glitching on at progress `p` (0 -> 1). `draw_logo(cv, tint)`
    draws the logo in its own colours when `tint` is None, or all in `tint`
    (for the colour ghosts). `box` (a vb.Box) is where the logo sits.

    The glitch changes on `steps` beats across the reveal, not every frame.
    Early beats often show nothing, so the logo flickers in; shown beats tear
    it into up to `slices` horizontal bands, some shifted sideways by up to
    `tear` of the box width, with `colors` ghosts offset `split` px either
    side. All of it shrinks to nothing by `settle`, after which the logo is
    clean. The same `seed` glitches the same way, frame for frame."""
    p = vb.clamp01(p)
    if p <= 0:
        return
    if p >= settle:
        draw_logo(cv, None)
        return
    step = int(p / settle * steps)
    rnd = random.Random(f'{seed}:{step}')
    k = step / steps                      # 0 -> 1 across the glitchy part
    if rnd.random() > 0.2 + 1.1 * k:      # dropouts: frequent early, gone late
        return
    amount = (1 - k) ** 0.8
    if rnd.random() < 0.4 * k * k:            # a clean beat now and then as it steadies
        draw_logo(cv, None)
        return
    # Uneven horizontal bands over the box, each torn sideways or not.
    cuts = sorted(rnd.uniform(0, 1) for _ in range(rnd.randint(2, slices - 1)))
    edges = [0.0] + cuts + [1.0]
    off = split * amount * (0.5 + rnd.random())
    for top, bottom in zip(edges, edges[1:]):
        y0, y1 = box.y + box.h * top, box.y + box.h * bottom
        dx = rnd.uniform(-1, 1) * tear * box.w * amount if rnd.random() < 0.6 else 0.0
        with cv.clip(0, y0, cv.width, y1 - y0):
            with cv.layer(opacity=0.85, dx=dx - off):
                draw_logo(cv, colors[0])
            with cv.layer(opacity=0.85, dx=dx + off):
                draw_logo(cv, colors[1])
            with cv.layer(dx=dx):
                draw_logo(cv, None)
    # A few stray blocks of broken signal around the logo.
    for _ in range(rnd.randint(1, 4)):
        bw, bh = box.w * rnd.uniform(0.1, 0.5) * (0.4 + amount), box.h * rnd.uniform(0.02, 0.07)
        bx = box.x + rnd.uniform(-0.2, 1.0) * box.w
        by = box.y + rnd.uniform(0, 1) * box.h
        cv.rect(bx, by, bw, bh, rnd.choice(colors + ('#ffffff',)), alpha=0.5 + 0.4 * amount)


# The demo's logo: a ring-and-dot mark with a wordmark beside it (plain shapes, not a real logo).
MARK, GAP = 150, 44


def _logo(cv, tint, x, y, f):
    cy = y + MARK / 2
    cv.arc(x + MARK / 2, cy, MARK * 0.4, 0, math.tau, tint or demo.ACCENT, width=MARK * 0.16)
    demo.dot(cv, x + MARK / 2, cy, MARK * 0.14, color=tint or demo.INK)
    w, h = vb.text.block_size(['NOVA'], f)
    vb.text.draw(cv, ['NOVA'], f, x + MARK + GAP, cy - h / 2, tint or demo.INK)


def draw(n, cv):
    f = demo.font(150, 900)
    w = MARK + GAP + vb.text.block_size(['NOVA'], f)[0]
    box = vb.Box((demo.W - w) / 2, (demo.H - MARK) / 2, w, MARK)
    glitch_reveal(cv, lambda c, tint: _logo(c, tint, box.x, box.y, f), box, demo.phase(n, 0.3, 2.2), seed=3)
    cv.mark('logo', *box)


TECHNIQUE = Technique(
    id='logo-glitch-reveal',
    name='Logo glitch reveal',
    family='shapes',
    group='Logo animation',
    aliases=('glitch logo', 'glitch logo reveal', 'digital distortion logo', 'RGB split logo reveal'),
    definition='A logo stutters into view like a corrupted signal, sliced and shoved sideways with '
               'red and cyan fringes, until the interference dies down and it sits still and clean.',
    phrasings=('make the logo glitch in like a broken TV signal',
               'reveal our logo with a digital distortion effect',
               'the logo flickers and tears with colour splits before it settles'),
    related=('station-id-bug', 'glitch-text', 'glitch-transition', 'light-trail-logo-reveal', 'glitch-sound',
             'line-draw-logo-reveal'),
    api=('videobuilder.techniques.shapes.logo_glitch_reveal.glitch_reveal',),
    demo=lambda: demo.film(draw),
)
