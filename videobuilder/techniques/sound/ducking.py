"""Ducking: videobuilder already has it as `vb.Audio(..., duck_db=-12)`, the
music dipping by that much while any `vb.Sound` that ducks it plays (speech,
a voice-over) and coming back up after, with its sound effects dipping along
with it. So this entry only names it and demos it: a steady bed of chimes and
a voice-like chatter of clicks over the middle second, and the bed's level
line sinking under it and rising again."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

DUCK_DB = -16
FG_START, FG_FRAMES = 27, 42                 # the foreground: frames 27..69 (0.9 s to 2.3 s)
RELEASE = 10                                 # frames the music takes to come back up; it drops at once
CHATTER = (0, 3, 5, 9, 12, 14, 19, 22, 24, 27, 31, 33, 36)   # the foreground's clicks, frames from FG_START
NOTES = ('G5', 'A5', None, 'A5')             # the bed's arpeggio (None: the ding's own pitch), every 7 frames
DINGS = tuple(range(0, 90, 7))
LANE_X0, LANE_X1 = 170, demo.W - 60
DOTS_Y, MUSIC_Y, FG_Y = 105, 300, 440        # the bed's dots, then the two lanes' baselines
LANE_H = 110


def level(n):
    """The music's gain in dB at frame `n`: 0, dropping by `DUCK_DB` as the
    foreground starts and rising over `RELEASE` frames as it ends, as the
    render's duck envelope does."""
    if n < FG_START:
        return 0.0
    return DUCK_DB * vb.clamp01((FG_START + FG_FRAMES - n) / RELEASE)


def gain(n):
    """`level(n)` as a linear gain: 1, down to about 0.16."""
    return 10 ** (level(n) / 20)


def fx(f):
    return LANE_X0 + (LANE_X1 - LANE_X0) * f / (demo.SECONDS * demo.FPS)


def draw(n, cv):
    label = demo.font(22, 700)

    # the bed: one dot per ding, sized by how loud the music was when it played
    vb.text.draw(cv, ['bed'], label, 40, DOTS_Y - 14, demo.MUTED)
    for f in DINGS:
        if n < f:
            demo.dot(cv, fx(f), DOTS_Y, 6, color=demo.MUTED, alpha=0.4)
            continue
        g, hit = gain(f), vb.clamp01(1 - (n - f) / 8)
        demo.dot(cv, fx(f), DOTS_Y, (6 + 16 * g) * (1 + 0.3 * hit), color=demo.TEAL, alpha=0.3 + 0.7 * g)

    # the music's level line, dipping under the foreground
    vb.text.draw(cv, ['music'], label, 40, MUSIC_Y - LANE_H / 2 - 12, demo.TEAL)
    cv.line(LANE_X0, MUSIC_Y, LANE_X1, MUSIC_Y, demo.LINE, width=2)
    for f in range(demo.FPS * 3):
        heard = f < n
        cv.line(fx(f), MUSIC_Y - LANE_H * gain(f), fx(f + 1), MUSIC_Y - LANE_H * gain(f + 1),
                demo.TEAL if heard else demo.MUTED, width=6 if heard else 2, alpha=1 if heard else 0.5)
    cv.mark('music', LANE_X0, MUSIC_Y - LANE_H, LANE_X1 - LANE_X0, LANE_H)

    # the foreground: its span, and a bar per click, lit as it plays
    vb.text.draw(cv, ['voice'], label, 40, FG_Y - 42, demo.ACCENT)
    cv.line(LANE_X0, FG_Y, LANE_X1, FG_Y, demo.LINE, width=2)
    x0, x1 = fx(FG_START), fx(FG_START + FG_FRAMES)
    cv.rect(x0, FG_Y - 62, x1 - x0, 64, demo.ACCENT, radius=8, alpha=0.18 if n >= FG_START else 0.06)
    for i, k in enumerate(CHATTER):
        f = FG_START + k
        amp = 52 * (0.55 + 0.45 * abs(math.sin(i * 2.3)))
        heard = f <= n
        cv.line(fx(f), FG_Y - 30 - amp / 2, fx(f), FG_Y - 30 + amp / 2, demo.ACCENT if heard else demo.MUTED,
                width=7, alpha=1 if heard else 0.45)

    # the playhead and the music's level under it
    x = fx(n)
    cv.line(x, MUSIC_Y - LANE_H - 30, x, FG_Y + 12, demo.INK, width=2, alpha=0.85)
    db = f'{level(n):.0f} dB' if level(n) < -0.5 else '0 dB'
    demo.word(cv, db, x, MUSIC_Y - LANE_H - 48, size=22, color=demo.INK, weight=800)


def film():
    ding = vb.sfx.get('pro_notify/ding_2045')
    bed = vb.Audio(ding.take(note=NOTES[0]).path, gain_db=-15, duck_db=DUCK_DB)   # the "music" file: the first ding
    dings = tuple(ding.sound(at=f, note=NOTES[i % len(NOTES)], gain_db=-15, align='onset')
                  for i, f in enumerate(DINGS) if i)
    # Plain `vb.Sound`s duck the music, as speech does; a chatter of clicks stands in for a voice. Each runs to
    # the end of the foreground, so the duck holds across the gaps; no fade-in, so the music drops at once.
    click = vb.sfx.get('fit/click/floss_lid').take().path
    end = FG_START + FG_FRAMES
    voice = tuple(vb.Sound(click, at=FG_START + k, start=0.0, frames=end - FG_START - k, gain_db=0,
                           fade_in_frames=0, fade_out_frames=RELEASE) for k in CHATTER)
    return demo.film(draw, audio=bed, sounds=dings + voice)


TECHNIQUE = Technique(
    id='ducking',
    name='Ducking',
    family='sound',
    group='Mixing & editing',
    aliases=('audio ducking', 'sidechain ducking', 'music ducking', 'dip the music', 'auto-duck'),
    definition='The background music drops to a lower level whenever a voice or other foreground sound plays, '
               'then swells back up as soon as it stops.',
    phrasings=('turn the music down while the narrator talks',
               'make the music dip under the voice-over',
               'lower the soundtrack when someone speaks and bring it back after'),
    related=('reverse-playback', 'silence-drop', 'music-bed', 'tape-wobble', 'mickey-mousing', 'reverse-cymbal'),
    api=('videobuilder.Audio', 'videobuilder.Sound'),
    demo=film,
)
