"""Audio-reactive particles: a cloud of dots around a centre that swells,
brightens and flings outward on every loud moment of the sound, then drifts
back as the sound falls away.

A film gets its per-frame loudness from videobuilder's own speech meter and
turns it into a 0 -> 1 drive with `drive`:

    samples, rate = vb.speech.read_samples(path)     # or any mono samples
    level = drive(vb.speech.levels(samples, rate, fps))
    travel = accumulate(level)
    draw_reactive_particles(cv, cx, cy, n / fps, level[n], travel=travel[n])

Every frame is drawn from `t` and the drive alone, so any frame renders on
its own, in any order.
"""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def drive(db, floor_db=-40.0, attack=0.7, release=0.2):
    """Per-frame levels in dB (0 at the loudest, as `vb.speech.levels`
    gives) as a smoothed 0 -> 1 drive: `floor_db` and below is 0, 0 dB is 1.
    It rises by `attack` of the gap each frame and falls by `release`, so a
    hit jumps up at once and fades over a few frames instead of flickering."""
    out, v = [], 0.0
    for d in db:
        target = vb.clamp01(1 - d / floor_db) if floor_db else 0.0
        v += (target - v) * (attack if target > v else release)
        out.append(v)
    return out


def accumulate(level, rate=1.0):
    """Running sum of a drive, so particles can travel further on loud
    stretches: pass item `n` as `travel` for frame `n`."""
    out, s = [], 0.0
    for v in level:
        s += v * rate
        out.append(s)
    return out


def particles(count, seed=0):
    """`count` particles as (angle, radius 0..1, size 0..1, speed, phase)
    tuples, the same for the same `seed`."""
    rnd = random.Random(seed)
    return [(rnd.uniform(0, 2 * math.pi), math.sqrt(rnd.random()), rnd.random(),
             rnd.uniform(0.4, 1.2) * rnd.choice((-1, 1)), rnd.uniform(0, 2 * math.pi)) for _ in range(count)]


def draw_reactive_particles(cv, cx, cy, t, level, travel=0.0, radius=110, burst=90, count=260, size=3.0,
                            color=demo.ACCENT, hot=demo.INK, seed=0, spin=0.25, kick=0.06):
    """Draw a particle cloud centred at (cx, cy) at time `t` seconds, pushed
    by `level` (0 -> 1, e.g. one item of `drive`). At rest the particles
    orbit slowly within `radius`; `level` throws each outward by up to
    `burst` (outer ones furthest), grows them up to 2.2 times `size` and
    shifts them from `color` towards `hot`. `travel` (from `accumulate`)
    adds `kick` radians of extra spin per unit, so loud passages also
    speed the swirl. Returns the Box the cloud can reach."""
    level = vb.clamp01(level)
    for a0, r0, s0, speed, ph in particles(count, seed):
        a = a0 + speed * (spin * t + kick * travel)
        wobble = 1 + 0.06 * math.sin(t * 2.3 + ph)
        r = (radius * (0.25 + 0.75 * r0)) * wobble + burst * level * (0.35 + 0.65 * r0)
        dot_r = size * (0.5 + s0) * (1 + 1.2 * level * (0.4 + 0.6 * s0))
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        mix = level * (0.3 + 0.7 * s0)
        if mix > 0.5:
            demo.dot(cv, x, y, dot_r * 1.8, color, alpha=0.15 * mix)  # a soft halo on the hottest
        demo.dot(cv, x, y, dot_r, color, alpha=0.55 + 0.45 * (1 - mix))
        if mix > 0.05:
            demo.dot(cv, x, y, dot_r, hot, alpha=mix * 0.9)
    reach = radius * 1.06 + burst + size * 6
    return vb.Box(cx - reach, cy - reach, 2 * reach, 2 * reach)


# ---- the demo: a made-up drum pattern stands in for the sound ----
HITS = (0.35, 0.85, 1.35, 1.6, 1.85, 2.35, 2.6)   # seconds; louder on the first and the run of three


def _demo_db():
    """A drum pattern's per-frame level in dB, as `vb.speech.levels` would
    measure it: each hit jumps to near 0 dB and decays, over a quiet bed."""
    out = []
    for n in range(round(demo.SECONDS * demo.FPS)):
        t = n / demo.FPS
        amp = 0.02 + sum((1.0 if i in (0, 3, 4) else 0.7) * math.exp(-(t - h) * 14)
                         for i, h in enumerate(HITS) if t >= h)
        out.append(20 * math.log10(min(1.0, amp)))
    return out


def _demo_sounds(id='pro_impact/short', gain_db=-5.0, soft_db=-3.0):
    """A drum hit from the sound pack at each time in HITS, landing on the
    first frame `_demo_db` lights for it, `soft_db` quieter on the softer
    hits, so the viewer hears what the particles burst on."""
    frames = [next(n for n in range(round(demo.SECONDS * demo.FPS)) if n / demo.FPS >= h) for h in HITS]
    return tuple(vb.sfx.sound(id, at=f, fps=demo.FPS, align='onset', dur=0.18,
                              gain_db=gain_db + (0.0 if i in (0, 3, 4) else soft_db))
                 for i, f in enumerate(frames))


LEVEL = drive(_demo_db(), floor_db=-30)
TRAVEL = accumulate(LEVEL)


def _meter(cv, n):
    """The sound itself along the bottom: bars of the drive, the current
    frame's lit, so the viewer sees what the particles answer to."""
    bars, x0, x1, y = len(LEVEL), 130, demo.W - 130, demo.H - 38
    step = (x1 - x0) / bars
    for i, v in enumerate(LEVEL):
        h = 3 + 26 * v
        lit = i <= n
        cv.rect(x0 + i * step, y - h / 2, max(1, step * 0.6), h, demo.TEAL if lit else demo.LINE,
                radius=1, alpha=1.0 if i == n else (0.75 if lit else 1.0))


def draw(n, cv):
    box = draw_reactive_particles(cv, demo.W / 2, demo.H / 2 - 25, n / demo.FPS, LEVEL[n], travel=TRAVEL[n],
                                  radius=85, burst=70, size=2.6, seed=3)
    cv.mark('particles', *box)
    _meter(cv, n)


CAPABILITY = Capability(
    id='audio-reactive-particles',
    name='Audio-reactive particles',
    family='particles',
    group='Audio-reactive',
    aliases=('music-reactive particles', 'sound-reactive particles', 'beat-reactive particles',
             'audio visualizer particles'),
    definition='A swarm of particles that bursts outward, grows and brightens on each loud beat of the '
               'soundtrack, then settles back to a slow drift in the quiet between.',
    phrasings=('particles that pulse with the music',
               'make the dots explode out on every beat of the track',
               'a glowing particle cloud that dances to the audio'),
    related=('sound-reactive-radial-shape', 'sound-bridge', 'turbulence-displacement', 'audio-waveform-bars',
             'image-to-particles', 'curl-noise-flow'),
    api=('videobuilder.capabilities.particles.audio_reactive_particles.draw_reactive_particles',
         'videobuilder.capabilities.particles.audio_reactive_particles.drive',
         'videobuilder.capabilities.particles.audio_reactive_particles.accumulate',
         'videobuilder.speech.levels'),
    demo=lambda: demo.film(draw, sounds=_demo_sounds()),
)
