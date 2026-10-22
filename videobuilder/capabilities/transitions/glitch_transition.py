"""Glitch transition: the frame shatters into horizontal bands that jump
sideways, with dropout bars, colour-channel tints and scanlines, and as the
bands re-roll each one flips from the outgoing scene to the incoming one."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

TINTS = ('#ff2bd6', '#00e5ff')  # a magenta and a cyan, standing in for split colour channels


def _bands(rng, h, count):
    """`count` horizontal bands of random height covering 0..h, as (y, height)."""
    cuts = sorted(rng.uniform(0, h) for _ in range(count - 1))
    edges = [0.0, *cuts, float(h)]
    return [(y0, y1 - y0) for y0, y1 in zip(edges, edges[1:]) if y1 - y0 > 0.5]


def glitch_transition(cv, a, b, p, seed=0, bands=16, shift=0.18, steps=18, scanlines=True):
    """Draw the glitch at progress `p` (0 -> 1). The frame is cut into about
    `bands` horizontal slices that re-roll `steps` times across the
    transition; each slice shows `a(cv)` or `b(cv)` (more of `b` as `p`
    grows), pushed sideways by up to `shift` of the frame width. The
    disturbance peaks mid-way and settles at both ends, so it cuts cleanly
    into and out of the two scenes. The same `seed` gives the same glitch.

    In a film, call it while two shots are live in an overlap, e.g.
    `glitch_transition(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    p = vb.clamp01(p)
    W, H = cv.width, cv.height
    step = min(int(p * steps), steps - 1)
    rng = random.Random(f'{seed}:{step}')
    power = math.sin(math.pi * p) ** 0.6           # 0 at the ends, 1 in the middle
    swap = _smooth(0.2, 0.8, p)                      # how much of the frame has gone over to `b`

    # A clean base under the slices, so gaps between moved bands show a scene, not a hole.
    (b if swap >= 0.5 else a)(cv)
    for y, h in _bands(rng, H, bands):
        scene = b if rng.random() < swap else a
        dx = rng.uniform(-1, 1) * shift * W * power if rng.random() < 0.75 else 0.0
        with cv.clip(0, y, W, h):
            with cv.layer(dx=dx):
                scene(cv)
            roll = rng.random()
            if roll < 0.18 * power:                   # a dead band: the signal drops out
                cv.fill('#000000', alpha=0.85)
            elif roll < 0.45 * power:                 # a channel slips: one colour floods the band
                cv.fill(rng.choice(TINTS), alpha=0.28)
        if dx and h > 6:                              # the torn edge: a hard colour fringe
            fringe = max(2.0, abs(dx) * 0.06)
            cv.rect(0, y, W, min(fringe, h), rng.choice(TINTS), alpha=0.6 * power)
    # A few small blocks of corrupted data, smeared across from elsewhere in the frame.
    for _ in range(int(6 * power)):
        bw, bh = rng.uniform(0.04, 0.16) * W, rng.uniform(0.01, 0.05) * H
        bx, by = rng.uniform(0, W - bw), rng.uniform(0, H - bh)
        with cv.clip(bx, by, bw, bh):
            with cv.layer(dx=rng.uniform(-0.3, 0.3) * W, dy=rng.uniform(-0.05, 0.05) * H):
                (b if rng.random() < swap else a)(cv)
    if scanlines and power > 0.05:
        for y in range(0, H, 6):
            cv.rect(0, y, W, 2, '#000000', alpha=0.22 * power)


def _smooth(e0, e1, x):
    t = vb.clamp01((x - e0) / (e1 - e0))
    return t * t * (3 - 2 * t)


CAPABILITY = Capability(
    id='glitch-transition',
    name='Glitch transition',
    family='transitions',
    group='Glitch',
    aliases=('digital glitch', 'VHS tracking transition', 'block glitch', 'datamosh transition',
             'signal glitch'),
    definition='The picture splits into horizontal strips that jerk sideways with dropouts, colour fringes '
               'and scanlines, and when the noise clears the next scene is in place.',
    phrasings=('glitch from this shot into the next one',
               'make the cut look like a broken digital signal',
               'a corrupted, jittery video switch between the two scenes'),
    related=('glitch-text', 'scanline-tear', 'pixelate-transition', 'scanline-jitter', 'glitch-sound',
             'screen-tearing'),
    api=('videobuilder.capabilities.transitions.glitch_transition.glitch_transition',),
    demo=lambda: demo.two_scenes(glitch_transition, start=0.9, length=1.2),
)
