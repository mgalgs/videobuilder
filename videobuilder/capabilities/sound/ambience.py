"""Ambience: a quiet, unbroken bed of background sound for a place (here,
wind) that runs under the whole scene. The pack has no ambience role, but the
first seconds of its long air risers are a steady hiss of wind before they
build, so `ambience_bed` loops those stretches, crossfaded, at a low level:
the air never drops out and never draws attention to itself."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

# (sound, take, from s, to s): stretches of the pack that hold a level, here steady air
WIND = (('riser/air', '4s', 0.0, 2.0), ('riser/rush', '4s', 0.0, 1.75))


def ambience_bed(first, last, fps=30, layers=WIND, gain_db=0.0, fade_s=0.5, sway_db=1.5):
    """`vb.Sound`s covering film frames `first` to `last` with a continuous
    bed: each of `layers` (a pack sound id, its take's variant or None, and
    the stretch of it to play, in seconds) taken in turn, each crossfading
    into the next over `fade_s`, so the joins don't show. Each sits `gain_db`
    from its take's level, give or take `sway_db`, so the bed breathes a
    little. They don't duck music. Put them in a film's `sounds`, e.g.
    `sounds=(*ambience_bed(0, FILM_FRAMES), HIT)`."""
    out, at, i = [], first, 0
    while at < last:
        id, variant, a, b = layers[i % len(layers)]
        take = vb.sfx.get(id).take(variant)
        a, b = min(a, take.dur_s), min(b, take.dur_s)
        frames = max(3, math.floor((b - a) * fps))
        fade = max(1, min(round(fade_s * fps), frames // 3))
        out.append(vb.Sound(take.path, at=at, start=a, frames=frames,
                            gain_db=gain_db + sway_db * math.sin(i * 2.399),   # golden-angle steps: never repeats
                            fade_in_frames=0 if at == first else fade, fade_out_frames=fade, ducks=False))
        at += frames - fade
        i += 1
    return tuple(out)


# ---- the demo: an open field in the wind, with the bed's level drawn as a steady strip ----
def _wave(x, t):
    return (math.sin(x * 0.013 + t * 2.1) + 0.6 * math.sin(x * 0.031 - t * 3.3)
            + 0.35 * math.sin(x * 0.071 + t * 5.7)) / 1.95


def draw(n, cv):
    t = n / demo.FPS
    W, H = demo.W, demo.H
    horizon = H * 0.62
    # sky glow and ground
    cv.rect(0, horizon, W, H - horizon, '#1b2a22')
    for k in range(6):
        cv.rect(0, horizon - 40 - k * 30, W, 30, demo.TEAL, alpha=0.035 * (6 - k))
    cv.line(0, horizon, W, horizon, demo.MUTED, width=2, alpha=0.6)
    # drifting streaks of air
    for k in range(14):
        speed = 260 + 90 * (k % 5)
        y = 120 + (k * 53) % int(horizon - 160)
        length = 120 + 60 * (k % 3)
        x = (k * 397 + t * speed) % (W + length + 200) - length - 100
        cv.line(x, y + 6 * math.sin(t * 2 + k), x + length, y + 6 * math.sin(t * 2 + k + 0.6),
                demo.INK, width=2, alpha=0.18 + 0.08 * (k % 3))
    # grass swaying under the gusts
    for k in range(90):
        x = 20 + k * (W - 40) / 89
        h = 50 + 40 * ((k * 37) % 7) / 6
        lean = 22 * _wave(x, t) + 10
        cv.line(x, horizon + 4, x + lean, horizon + 4 - h, '#6f9a6a', width=3, alpha=0.85)
    # the bed: a low, continuous strip of level that never stops and never spikes
    y0, band = H * 0.8, 46
    cv.rect(80, y0 - band - 10, W - 160, 2 * band + 20, '#000000', radius=14, alpha=0.25)
    for k in range(150):
        x = 100 + k * (W - 200) / 149
        a = band * (0.28 + 0.12 * _wave(x * 3.1, t * 1.7) + 0.05 * math.sin(k * 1.7 + t * 23))
        cv.line(x, y0 - a, x, y0 + a, demo.TEAL, width=4, alpha=0.8)
    demo.word(cv, 'AMBIENCE  ·  wind bed, under everything', W / 2, H - 36, size=30, color=demo.MUTED,
              weight=700)


def _wind():
    # the full pack has the air risers; a cut-down pack (the tests') falls back to any whoosh it has
    have = vb.sfx.bank().effects
    return tuple(w for w in WIND if w[0] in have) or tuple((e.id, None, 0.0, 9.0) for e in vb.sfx.find('whoosh'))


def film():
    frames = round(demo.SECONDS * demo.FPS)
    return demo.film(draw, sounds=ambience_bed(0, frames, demo.FPS, layers=_wind()), loudness=-20.0)


CAPABILITY = Capability(
    id='ambience',
    name='Ambience',
    family='sound',
    group='Mixing & editing',
    aliases=('ambient sound', 'atmos', 'background ambience', 'atmosphere', 'room tone'),
    definition='A soft, steady layer of the sound a location would have, like wind, traffic or a murmuring '
               'room, running underneath a scene so it feels like a real place.',
    phrasings=('put some quiet wind under this shot',
               'add a background soundscape so it feels like we are outside',
               'give the scene a low bed of room noise'),
    related=('music-bed', 'atmospheric-fog', 'foley', 'aurora-gradient-background', 'fractal-brownian-motion',
             'ui-sound-effects'),
    api=('videobuilder.capabilities.sound.ambience.ambience_bed', 'videobuilder.Sound', 'videobuilder.sfx.get'),
    demo=film,
)
