"""Riser: a sound that keeps climbing for a second or few, higher, louder,
denser, and stops dead on the frame the big thing appears, so the viewer
leans in before the reveal.

`riser` places one from the bundled pack so its peak (the very end of the
build) lands on the reveal frame, picking the take whose length is nearest
the build, with an optional hit on the same frame to land it:

    REVEAL = 66
    sounds = riser(REVEAL, build=2.0)                 # starts ~2 s earlier, peaks on frame 66
    vb.Film(..., sounds=sounds)

`pulse_riser` builds one out of short sounds instead, coming faster and
louder into the reveal, for a pack with no riser takes.

The demo builds for two seconds, a waveform wedge filling left to right as
it gets taller and tighter, the frame trembling harder, then a card pops on
the riser's last frame with a flash.
"""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def riser(reveal, build=2.0, id='pro_riser/air_gate', hit='pro_impact/short', fps=30, gain_db=-6.0,
          hit_gain_db=-8.0):
    """The sounds for a riser into frame `reveal`: the pack riser `id`, its
    take nearest `build` seconds long, with its peak (where the build tops
    out) on `reveal`, plus `hit` (a pack id, or None for none) peaking on the
    same frame. Returns the placed `vb.sfx` sounds, for `Film(sounds=...)`."""
    sounds = [vb.sfx.sound(id, at=reveal, fps=fps, dur=build, gain_db=gain_db)]
    if hit:
        sounds.append(vb.sfx.sound(hit, at=reveal, fps=fps, gain_db=hit_gain_db))
    return tuple(sounds)


def pulse_times(reveal, build, count, fps=30, bunch=1.5):
    """The film frames of `count` pulses over the `build` seconds before
    frame `reveal`, the last on `reveal`, the gaps shrinking towards it."""
    return tuple(round(reveal - build * fps * (1 - k / (count - 1)) ** bunch) for k in range(count))


def pulse_riser(reveal, build=2.0, id='whoosh_fast/tight', count=8, hit='pro_impact/short', fps=30,
                quiet_db=-24.0, loud_db=-6.0, hit_gain_db=-8.0):
    """A riser made of short pack sounds when no riser take suits: `count`
    of `id`, coming faster and louder (from `quiet_db` to `loud_db`) over
    the `build` seconds into `reveal`, the last peaking on it, plus `hit`
    (or None). Returns the placed `vb.sfx` sounds."""
    frames = pulse_times(reveal, build, count, fps)
    sounds = [vb.sfx.sound(id, at=f, fps=fps, dur=0.25, gain_db=quiet_db + (loud_db - quiet_db) * k / (count - 1))
              for k, f in enumerate(frames)]
    if hit:
        sounds.append(vb.sfx.sound(hit, at=reveal, fps=fps, gain_db=hit_gain_db))
    return tuple(sounds)


# ---- the demo: a two-second build, a card on its last frame ----
START, REVEAL_S = 0.3, 2.3
REVEAL = round(REVEAL_S * demo.FPS)
BARS = 46
X0, X1 = 180, demo.W - 180
BASE_Y = demo.H / 2 + 190


def _bar_x(i):
    """Bars bunch up towards the right: the build gets denser as it climbs."""
    u = i / (BARS - 1)
    return X0 + (X1 - X0) * (1 - (1 - u) ** 1.6)


def _wedge(cv, n, p):
    """The riser drawn as its own shape: bars rising left to right, lit up to
    the playhead, wobbling faster and harder as the build nears its top."""
    t = n / demo.FPS
    for i in range(BARS):
        u = i / (BARS - 1)
        lit = u <= p
        wob = 0.75 + 0.25 * math.sin(t * (8 + 40 * u) + i * 1.3) if lit else 1.0
        h = (14 + 260 * u ** 1.8) * wob
        x = _bar_x(i)
        cv.line(x, BASE_Y, x, BASE_Y - h, demo.ACCENT if lit else demo.LINE, width=7,
                alpha=0.55 + 0.45 * u if lit else 0.7)
    px = X0 + (X1 - X0) * p
    cv.line(px, BASE_Y + 24, px, BASE_Y - 300, demo.INK, width=2, alpha=0.8 if p < 1 else 0)
    demo.word(cv, 'riser', (X0 + X1) / 2, BASE_Y + 56, size=28, color=demo.MUTED, weight=700)


def draw(n, cv):
    t = n / demo.FPS
    p = demo.phase(n, START, REVEAL_S)
    after = t - REVEAL_S
    if after < 0:
        shake = 10 * p ** 3                                   # trembling harder as it climbs
        dx, dy = shake * math.sin(t * 61), shake * math.cos(t * 47)
        cv.rect(demo.W / 2 - 150 + dx, demo.H / 2 - 230 + dy, 300, 180, demo.LINE, radius=18,
                alpha=0.25 + 0.5 * p)
        _wedge(cv, n, p)
        return
    q = vb.clamp01(after / 0.35)
    with cv.layer(opacity=1 - q):
        _wedge(cv, n, 1.0)
    demo.card(cv, demo.W / 2, demo.H / 2 - 140, w=360, h=220, scale=0.6 + 0.4 * vb.ease_out_back(q))
    demo.word(cv, 'reveal', demo.W / 2, demo.H / 2 + 80, size=64, alpha=q)
    flash = max(0.0, 1 - after / 0.25)
    if flash > 0:
        cv.fill('#ffffff', alpha=0.7 * flash)


def film():
    build = REVEAL_S - START
    if 'riser' in vb.sfx.roles():
        return demo.film(draw, sounds=riser(REVEAL, build=build))
    return demo.film(draw, sounds=pulse_riser(REVEAL, build=build))   # a pack without risers


CAPABILITY = Capability(
    id='riser',
    name='Riser',
    family='sound',
    group='Sound effects',
    aliases=('uplifter', 'build-up', 'tension riser', 'rising sound'),
    definition='A sound that keeps getting higher and louder for a couple of seconds and cuts off at its '
               'top on the exact frame something big appears.',
    phrasings=('build some tension right before the logo shows up',
               'add a rising whoosh that climbs into the reveal',
               'make the sound swell up and hit when the title lands'),
    related=('music-swell', 'pulse-loader', 'liquid-fill-level', 'sound-bridge', 'stacked-bar-build',
             'anticipation'),
    api=('videobuilder.capabilities.sound.riser.riser', 'videobuilder.capabilities.sound.riser.pulse_riser',
         'videobuilder.sfx.sound', 'videobuilder.sfx.find'),
    demo=film,
)
