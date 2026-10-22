"""Glitch sound: a short burst of stuttering digital noise, placed so the
picture breaks up while it plays and snaps back clean on its peak."""
import dataclasses
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

GLITCHES = ('pro_glitch/standard', 'pro_glitch/fastroll', 'pro_glitch/crunchy', 'pro_glitch/framelock',
            'pro_glitch/data', 'pro_glitch/sparse')


def glitch_sound(at, id='pro_glitch/standard', fps=30, gain_db=-8, dur=None):
    """A glitch burst from the sound-effects pack (`GLITCHES`, or the
    `glitch/*` set) as a `vb.sfx` sound whose peak, the hard stop the
    stutter builds to, lands on film frame `at`: put it on the cut, or on the
    frame the picture snaps back. It plays from `s.at` to `s.mark`, the span
    the picture should be breaking up over (see `glitch_amount`)."""
    return vb.sfx.sound(id, at=at, fps=fps, gain_db=gain_db, dur=dur)


def stutter(id, at, frames=18, fps=30, gain_db=-8, seed=0, gate=0.2, variant=None):
    """Any sound in the pack chopped into a glitch: one-frame grains taken
    from just before its peak, each repeated a few frames then jumping,
    some frames dropped (`gate`), over the `frames` frames up to `at`, where
    the sound plays on from its peak to its end. A tuple of `vb.sfx` sounds
    for `Film(sounds=...)`; it plays from its first `at` to its last `mark`."""
    take = vb.sfx.get(id).take(variant)
    r = random.Random(f'{id}:{seed}')
    step = 1 / fps
    grains = [max(0.0, take.peak_s - k * 1.5 * step) for k in range(1, 5)]

    def piece(f, start, length):
        return dataclasses.replace(take.sound(f, fps, align='onset', gain_db=gain_db), at=f, start=start,
                                   frames=length, fade_in_frames=0, fade_out_frames=0, mark=f, sync_s=start,
                                   take=None)   # placed by hand: Film keeps it where it is

    out, grain, left = [], grains[0], 0
    for f in range(at - frames, at):
        if left <= 0:
            grain, left = r.choice(grains), r.randint(1, 4)
        left -= 1
        if r.random() >= gate:
            out.append(piece(f, grain, 1))
    tail = max(1, math.ceil((take.dur_s - take.peak_s) * fps))
    out.append(dataclasses.replace(piece(at, take.peak_s, tail), fade_out_frames=min(3, tail - 1)))
    return tuple(out)


def _span(burst):
    parts = burst if isinstance(burst, (tuple, list)) else (burst,)
    return min(s.at for s in parts), max(s.mark for s in parts)


def glitch_amount(n, bursts, seed=0, gate=0.3):
    """How hard the picture should glitch on frame `n` (0 -> 1), given the
    placed `bursts` (each a `glitch_sound`, or a `stutter`'s tuple): zero
    outside every burst; inside one it climbs from its first frame to 1 on
    its peak frame, with about `gate` of the frames dropped to zero so the
    image stutters with the noise. Same `seed`, same frames."""
    best = 0.0
    for i, burst in enumerate(bursts):
        first, peak = _span(burst)
        if n == peak:
            return 1.0
        if first <= n < peak:
            r = random.Random(f'{seed}:{i}:{n}')
            if r.random() >= gate:
                p = (n - first + 1) / (peak - first + 1)
                best = max(best, (0.35 + 0.65 * p) * (0.6 + 0.4 * r.random()))
    return best


BURSTS = ((36, 'pro_glitch/standard'), (76, 'pro_glitch/fastroll'))   # (peak frame, sound)
STAND_IN = 'whoosh_fast/tight'   # chopped by `stutter` when the pack in use has no glitch sounds


def _scene(cv, color, n, amount):
    demo.word(cv, 'SIGNAL', demo.W / 2, demo.H / 2 - 60, color=color, font=demo.mono(220, 800))
    # a level meter: flat while it is quiet, jumping while the noise plays
    bars, gap, y = 48, 22, demo.H / 2 + 170
    x0 = (demo.W - (bars - 1) * gap) / 2
    for b in range(bars):
        h = 6 + amount * 150 * random.Random(f'm:{n}:{b}').random()
        cv.rect(x0 + b * gap - 5, y - h / 2, 10, h, color, radius=5, alpha=0.85)


def draw(n, cv, bursts):
    amount = glitch_amount(n, bursts, seed=3)
    if amount <= 0:
        _scene(cv, demo.INK, n, 0)
    else:
        split = 18 * amount   # colour fringes either side
        with cv.layer(opacity=0.8, dx=-split):
            _scene(cv, demo.ACCENT, n, amount)
        with cv.layer(opacity=0.8, dx=split):
            _scene(cv, demo.TEAL, n, amount)
        r = random.Random(f'tear:{n}')
        y = 0
        while y < demo.H:   # tear the picture into bands, some shoved sideways
            band = r.uniform(20, 140)
            dx = r.uniform(-1, 1) * 160 * amount if r.random() < 0.45 else 0
            with cv.clip(0, y, demo.W, band), cv.layer(dx=dx):
                if dx:
                    cv.fill(demo.BG, alpha=0.55)
                _scene(cv, demo.INK, n, amount)
            y += band
    cv.mark('signal', 0, 0, demo.W, demo.H)


def make_demo():
    # placed here, not at import, so the registry loads without the pack
    if all(id in vb.sfx.bank().effects for _, id in BURSTS):
        bursts = tuple(glitch_sound(at, id) for at, id in BURSTS)
        sounds = bursts
    else:
        bursts = tuple(stutter(STAND_IN, at, frames=20, seed=i) for i, (at, _) in enumerate(BURSTS))
        sounds = tuple(s for b in bursts for s in b)
    return demo.film(lambda n, cv: draw(n, cv, bursts), sounds=sounds)


TECHNIQUE = Technique(
    id='glitch-sound',
    name='Glitch sound',
    family='sound',
    group='Sound effects',
    aliases=('glitch SFX', 'data glitch sound', 'digital stutter'),
    definition='A quick burst of crackling, stuttering digital noise that plays while the picture tears '
               'and jitters, then cuts out the moment the image snaps back.',
    phrasings=('add a broken-signal noise when the title glitches',
               'make it sound like the video is malfunctioning for a second',
               'a buzzy digital stutter under the glitch effect'),
    related=('glitch-text', 'glitch-transition', 'static-noise', 'data-bending', 'logo-glitch-reveal',
             'silence-drop'),
    api=('videobuilder.techniques.sound.glitch_sound.glitch_sound',
         'videobuilder.techniques.sound.glitch_sound.glitch_amount',
         'videobuilder.techniques.sound.glitch_sound.stutter',
         'videobuilder.sfx.sound'),
    demo=make_demo,
)
