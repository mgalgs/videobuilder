"""Falling Letter Rain: loose letters fall from above the frame like a shower,
speeding up under gravity and tumbling as they go, nearer ones bigger and
faster than the ones behind, so the screen fills with a steady downpour."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

GLYPHS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'


def letter_rain(t, width, height, count=75, seed=0, glyphs=GLYPHS, sizes=(26, 110), gravity=1500,
                speed=(80, 320), spin=1.2):
    """The rain at `t` seconds over a `width` x `height` frame, as a list of
    `(char, x, y, size, angle, depth)` drops, far ones first so nearer ones draw
    over them. `(x, y)` is the letter's centre, `angle` its tilt in radians and
    `depth` 0 (far) -> 1 (near). Each of `count` drops falls from just above the
    top, starting at a random speed in `speed` px/s and accelerating at
    `gravity` px/s^2 (scaled down for far drops), then re-enters at the top
    with a new letter and column, so the shower never thins out; at `t = 0`
    it is already mid-fall. `sizes` is the font size range far -> near and
    `spin` the most a letter turns per second. The same `seed` gives the same
    rain, frame for frame."""
    drops = []
    for i in range(count):
        r = random.Random(f'{seed}:{i}')
        depth = r.random()
        size = sizes[0] + (sizes[1] - sizes[0]) * depth
        g = gravity * (0.45 + 0.55 * depth)
        v0 = speed[0] + (speed[1] - speed[0]) * r.random()
        dist = height + 2 * size
        period = (-v0 + math.sqrt(v0 * v0 + 2 * g * dist)) / g
        tt = t + r.random() * period  # stagger: everyone starts somewhere along their fall
        cycle, tau = divmod(tt, period)
        c = random.Random(f'{seed}:{i}:{int(cycle)}')
        x = c.uniform(0, width)
        y = -size + v0 * tau + 0.5 * g * tau * tau
        angle = c.uniform(-0.4, 0.4) + c.uniform(-spin, spin) * tau
        drops.append((c.choice(glyphs), x, y, size, angle, depth))
    drops.sort(key=lambda d: d[5])
    return drops


def draw_letter_rain(cv, t, width=None, height=None, color=demo.INK, far=None, font=None, weight=800, **kw):
    """Draw `letter_rain` at `t` seconds across the canvas (or the `width` x
    `height` area at its top-left). Letters are `color`, fainter the farther
    they are; with `far` given, the back half are `far` instead. `font(size,
    weight)` makes the font (default: the kit's). `kw` goes to `letter_rain`."""
    width = cv.width if width is None else width
    height = cv.height if height is None else height
    make = font or demo.font
    c = cv.ctx
    for ch, x, y, size, angle, depth in letter_rain(t, width, height, **kw):
        f = make(round(size), weight)
        w, h = vb.text.block_size([ch], f)
        c.save()
        c.translate(x, y)
        c.rotate(angle)
        if far is None:
            vb.text.draw(cv, [ch], f, -w / 2, -h / 2, color, alpha=0.3 + 0.7 * depth)
        else:
            vb.text.draw(cv, [ch], f, -w / 2, -h / 2, far if depth < 0.5 else color,
                         alpha=0.55 + 0.45 * depth)
        c.restore()


def draw(n, cv):
    draw_letter_rain(cv, n / demo.FPS, color=demo.INK, far=demo.TEAL, seed=3)
    cv.mark('rain', 0, 0, demo.W, demo.H)


TECHNIQUE = Technique(
    id='falling-letter-rain',
    name='Falling letter rain',
    family='typography',
    group='Physics and particles',
    aliases=('letter rain', 'raining letters', 'alphabet rain', 'falling letters'),
    definition='Scattered letters pour down the screen like a rain shower, accelerating and '
               'tumbling as they fall, with bigger near letters passing in front of smaller far ones.',
    phrasings=('make it rain letters',
               'a shower of random letters falling down the screen',
               'letters dropping from the sky like rain behind the title'),
    related=('falling-glyph-rain-reveal', 'character-drop', 'rainfall', 'matrix-digital-rain',
             'rain-on-glass', 'meteor-shower'),
    api=('videobuilder.techniques.typography.falling_letter_rain.draw_letter_rain',
         'videobuilder.techniques.typography.falling_letter_rain.letter_rain'),
    demo=lambda: demo.film(draw),
)
