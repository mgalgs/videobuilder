"""Frame stutter: playback hitches at uneven moments -- the picture sticks on
one frame for a few beats, then lurches ahead to catch up -- like video on a
struggling player or a dropped-frame feed."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def frame_stutter(n, seed=0, chance=0.3, longest=5, start=0):
    """The frame to show at film frame `n` when playback stutters from frame
    `start` on. Walking forward from `start`, each shown frame either plays
    for one frame or, with probability `chance`, sticks for 2 to `longest`
    frames; after a stick the clock jumps straight to real time, so the
    frames it covered are dropped and the motion lurches ahead. The pattern is
    fixed by `seed`, so it is the same on every render.

    In a film, draw the stuttering layer at the returned frame instead of
    `n`, e.g. `scene(cv, frame_stutter(n, seed=3))`; the rest of the film can
    keep running smoothly."""
    if n < start:
        return n
    rng = random.Random(f'frame-stutter:{seed}')
    shown = start
    while True:
        hold = rng.randint(2, max(2, longest)) if rng.random() < chance else 1
        if n < shown + hold:
            return shown
        shown += hold


def stutter_jumped(n, seed=0, chance=0.3, longest=5, start=0):
    """Whether frame `n` is the first frame after a stick, the moment the
    picture lurches ahead -- a place to add a jolt, a tear or a click."""
    return n > start and frame_stutter(n - 1, seed, chance, longest, start) < n - 1 \
        and frame_stutter(n, seed, chance, longest, start) == n


SEED, CHANCE, LONGEST = 4, 0.35, 6
Y = demo.H / 2 + 30


def _scene(cv, f):
    """The subject at frame `f`: a card gliding across in a run of low hops."""
    p = vb.ease_in_out_quart(demo.phase(f, 0.15, 2.85))
    x = 220 + (demo.W - 440) * p
    demo.floor(cv, Y + 130)
    y = Y - 60 * abs(math.sin(f / demo.FPS * 5))
    demo.card(cv, x, y)


def draw(n, cv):
    shown = frame_stutter(n, SEED, CHANCE, LONGEST)
    jolt = 10 if stutter_jumped(n, SEED, CHANCE, LONGEST) else 0
    with cv.layer(dy=jolt):
        _scene(cv, shown)
    # real time keeps running smoothly across the top; the frame counter does not
    y, x0, x1 = 60, 80, demo.W - 300
    cv.line(x0, y, x1, y, demo.LINE, width=2)
    demo.dot(cv, x0 + (x1 - x0) * n / (demo.FPS * demo.SECONDS - 1), y, 6, color=demo.INK)
    stuck = shown != n
    vb.text.draw(cv, [f'FRAME {shown:03d}'], demo.mono(26, 700), demo.W - 250, y - 16,
                 demo.ACCENT if stuck else demo.MUTED)


CAPABILITY = Capability(
    id='frame-stutter',
    name='Frame stutter',
    family='vfx',
    group='Time displacement',
    aliases=('stutter', 'frame drop', 'dropped frames', 'lag stutter', 'playback hitch'),
    definition='The motion keeps catching on single frames for uneven little beats and then skipping '
               'ahead, as if the playback were lagging.',
    phrasings=('make it look like the video is lagging and dropping frames',
               'add a choppy hitch to the movement, like a bad stream',
               'have the footage freeze for a moment here and there then jump forward'),
    related=('stutter-cut', 'screen-tearing', 'scanline-jitter', 'wiggle-path', 'smooth-scroll-inertia',
             'slow-motion'),
    api=('videobuilder.capabilities.vfx.frame_stutter.frame_stutter',
         'videobuilder.capabilities.vfx.frame_stutter.stutter_jumped'),
    demo=lambda: demo.film(draw),
)
