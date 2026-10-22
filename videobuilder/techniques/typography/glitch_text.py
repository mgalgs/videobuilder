"""Glitch Text: a word that holds steady, then breaks up in short bursts --
horizontal slices tear sideways, red and cyan copies split off either side,
the whole line twitches -- before snapping clean again."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

SPLIT = ('#ff2d55', '#1fd8ff')


def glitch_bursts(t, bursts, attack=0.04, release=0.12):
    """How glitched the text is at `t` seconds, 0 -> 1, given `bursts` as
    `(start, length)` pairs in seconds: each snaps up over `attack`, holds,
    and dies away over `release`. Feed the result to `draw_glitch` as `amount`."""
    out = 0.0
    for start, length in bursts:
        if t < start or t > start + length + release:
            continue
        if t < start + attack:
            a = (t - start) / attack
        elif t <= start + length:
            a = 1.0
        else:
            a = 1 - (t - start - length) / release
        out = max(out, a)
    return vb.clamp01(out)


def draw_glitch(cv, text, font, x, y, color, amount, tick, seed=0, split=SPLIT, slices=7, shift=None):
    """Draw `text` from its top-left (x, y) glitched by `amount` (0 clean,
    1 fully broken). `tick` picks the random pattern (pass the frame number,
    or a slower step of it for a choppier glitch); the same `seed` and `tick`
    always tear the same way. The line is cut into up to `slices` horizontal
    bands, some shoved sideways by up to `shift` px (default a third of the
    font size), and two copies in the `split` colours peel off left and
    right. Returns the Box of the clean line."""
    w, h = vb.text.block_size([text], font)
    if amount <= 0:
        vb.text.draw(cv, [text], font, x, y, color)
        return vb.Box(x, y, w, h)
    rnd = random.Random(f'{seed}:{tick}')
    shift = font.size / 3 if shift is None else shift
    jx, jy = rnd.uniform(-1, 1) * shift * 0.15 * amount, rnd.uniform(-1, 1) * shift * 0.05 * amount
    rgb = shift * 0.35 * amount * (0.6 + 0.4 * rnd.random())

    def stack(dx):
        left, right = split
        vb.text.draw(cv, [text], font, x + dx + jx - rgb, y + jy, left, alpha=0.85)
        vb.text.draw(cv, [text], font, x + dx + jx + rgb, y + jy, right, alpha=0.85)
        vb.text.draw(cv, [text], font, x + dx + jx, y + jy, color)

    # Uneven band edges across the line (padded so the jolt never clips the glyphs).
    pad = shift
    cuts = sorted(rnd.uniform(0, h) for _ in range(slices - 1))
    edges = [y - pad] + [y + c for c in cuts] + [y + h + pad]
    for top, bottom in zip(edges, edges[1:]):
        dx = 0.0
        if rnd.random() < 0.55 * amount + 0.1:
            dx = rnd.uniform(-1, 1) * shift * amount
        with cv.clip(x - w - 2 * shift, top, 3 * w + 4 * shift, bottom - top):
            stack(dx)
    # A thin bright scan bar or two through the line at the worst moments.
    for _ in range(int(amount * 2.5)):
        by = y + rnd.uniform(0, h)
        cv.rect(x + rnd.uniform(-0.1, 0.3) * w, by, w * rnd.uniform(0.3, 0.8), max(2.0, h * 0.03),
                rnd.choice(split), alpha=0.7 * amount)
    return vb.Box(x, y, w, h)


BURSTS = ((0.45, 0.3), (1.3, 0.12), (1.65, 0.45), (2.55, 0.1))


def draw(n, cv):
    f = demo.font(150, 900)
    text = 'GLITCH'
    w, h = vb.text.block_size([text], f)
    t = n / demo.FPS
    amount = glitch_bursts(t, BURSTS)
    # A low hum of instability between bursts, so the line never quite trusts itself.
    amount = max(amount, 0.12 if math.sin(t * 23) > 0.97 else 0.0)
    box = draw_glitch(cv, text, f, (demo.W - w) / 2, (demo.H - h) / 2, demo.INK, amount, n // 2, seed=3)
    cv.mark('text', *box)


TECHNIQUE = Technique(
    id='glitch-text',
    name='Glitch text',
    family='typography',
    group='Glitch and distortion',
    aliases=('glitch effect', 'RGB split text', 'digital distortion text', 'datamosh title'),
    definition='Type that sits still until it suddenly tears into sideways-shifted slices with red and '
               'cyan copies splitting off it, then snaps back to clean.',
    phrasings=('make the title glitch out like a broken screen',
               'the words should flicker and tear like a corrupted signal',
               'give the headline a digital glitch with colour split'),
    related=('glitch-transition', 'data-bending', 'glitch-sound', 'logo-glitch-reveal', 'pixelation-reveal',
             'scramble-decode'),
    api=('videobuilder.techniques.typography.glitch_text.draw_glitch',
         'videobuilder.techniques.typography.glitch_text.glitch_bursts'),
    demo=lambda: demo.film(draw),
)
