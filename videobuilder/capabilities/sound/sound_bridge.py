"""Sound bridge: one musical phrase plays straight through a hard cut, so the
picture changes but the sound doesn't, and the two shots feel joined.

`sound_bridge` lays a run of tuned notes from the bundled pack across a cut
frame, some landing before it and the rest after, evenly spaced, so nothing
in the sound marks where the picture jumps:

    CUT = 45
    sounds = sound_bridge(CUT, ('C5', 'E5', 'G5', 'C6', 'B5', 'G5'), step=8, before=3)
    vb.Film(..., sounds=sounds)

The demo cuts from scene A to scene B halfway, one figure of dings running
on through it at the same pace, the phrase drawn as a lane across the bottom
of both shots.
"""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def bridge_frames(cut, count, step, before):
    """The film frames `count` notes land on, one every `step` frames, the
    first `before` of them before frame `cut` and the rest on or after it
    (the cut sits half a step after the last note before it)."""
    first = cut - before * step + step // 2
    return tuple(first + i * step for i in range(count))


def sound_bridge(cut, notes, step=8, before=None, id='pluck/kalimba', fps=30, gain_db=-8.0):
    """A phrase of tuned sounds that carries across the cut at frame `cut`:
    `notes` (e.g. 'C5', 'E5') of the pack sound `id`, one every `step`
    frames, `before` of them (default half) ahead of the cut and the rest
    after it. Each note rings out over the next, so the sound is unbroken at
    the cut. Returns the placed `vb.sfx` sounds, for `Film(sounds=...)`."""
    if before is None:
        before = len(notes) // 2
    frames = bridge_frames(cut, len(notes), step, before)
    return tuple(vb.sfx.sound(id, at=f, fps=fps, note=note, gain_db=gain_db) for f, note in zip(frames, notes))


# ---- the demo: a hard cut halfway, a phrase running through it ----
CUT = round(1.5 * demo.FPS)
SOUND = 'pro_notify/ding_2045'                         # short dings, each ringing into the next
NOTES = ('G5', 'G5', 'A5', 'G5') * 2                   # one figure, played on both sides of the cut
STEP = 9
FRAMES = bridge_frames(CUT, len(NOTES), STEP, before=4)
_HIGH = {'G5': 0.0, 'A5': 1.0}
LANE_Y, LANE_H = demo.H - 105, 80
X0, X1 = 140, demo.W - 140


def _fx(f):
    return X0 + (X1 - X0) * f / (demo.SECONDS * demo.FPS)


def _lane(cv, n):
    """The phrase as notes on a strip across the bottom: one dot per note at
    its pitch, lit once it has sounded and ringing out as a fading tail
    across the cut line, with a playhead."""
    cv.rect(X0 - 40, LANE_Y - LANE_H / 2 - 20, X1 - X0 + 80, LANE_H + 40, demo.BG, radius=18, alpha=0.82)
    cx = _fx(CUT)
    cv.line(cx, LANE_Y - LANE_H / 2 - 8, cx, LANE_Y + LANE_H / 2 + 8, demo.MUTED, width=2, alpha=0.9)
    demo.word(cv, 'cut', cx, LANE_Y - LANE_H / 2 - 42, size=24, color=demo.INK, weight=700)
    x0, px = _fx(FRAMES[0]), _fx(n)
    if px > x0:   # the sound itself: one band, unbroken through the cut
        end = min(px, _fx(FRAMES[-1] + STEP))
        cv.rect(x0, LANE_Y - 3, end - x0, 6, demo.TEAL, radius=3, alpha=0.8)
    pts = []
    for f, note in zip(FRAMES, NOTES):
        y = LANE_Y + LANE_H * (0.22 - 0.44 * _HIGH[note])
        pts.append((_fx(f), y, f))
    for (x, y, f), (x2, _, _) in zip(pts, pts[1:] + [(_fx(FRAMES[-1] + STEP * 2), 0, 0)]):
        if n >= f:   # the note's ring, reaching on under the next one
            end = min(x2 + (x2 - x) * 0.6, _fx(n))
            cv.line(x, y, max(x, end), y, demo.ACCENT, width=6, alpha=0.45)
    for x, y, f in pts:
        age = (n - f) / demo.FPS
        if age >= 0:
            pulse = math.exp(-age * 6)
            demo.dot(cv, x, y, 13 + 12 * pulse, demo.ACCENT, alpha=0.25 * pulse)
            demo.dot(cv, x, y, 11, demo.ACCENT)
        else:
            demo.dot(cv, x, y, 9, demo.LINE)
    cv.line(px, LANE_Y - LANE_H / 2 - 8, px, LANE_Y + LANE_H / 2 + 8, demo.INK, width=3)
    cv.mark('lane', X0 - 40, LANE_Y - LANE_H / 2 - 20, X1 - X0 + 80, LANE_H + 40)


def draw(n, cv):
    (demo.scene_a if n < CUT else demo.scene_b)(cv)   # a plain hard cut: the picture jumps
    _lane(cv, n)


def film():
    return demo.film(draw, sounds=sound_bridge(CUT, NOTES, step=STEP, before=4, id=SOUND, fps=demo.FPS,
                                                gain_db=-10))


TECHNIQUE = Technique(
    id='sound-bridge',
    name='Sound bridge',
    family='sound',
    group='Mixing & editing',
    aliases=('audio bridge', 'sound transition', 'J-cut', 'L-cut'),
    definition='The same sound or phrase of music keeps playing straight through a cut, '
               'so the picture changes while the audio carries the viewer smoothly into the next shot.',
    phrasings=('keep the music going across the cut so the scenes feel connected',
               'let the sound from the first shot carry over into the second',
               'tie the two scenes together with audio that runs through the edit'),
    related=('silence-drop', 'whoosh', 'foley', 'audio-reactive-particles', 'music-bed', 'reverse-playback'),
    api=('videobuilder.techniques.sound.sound_bridge.sound_bridge',
         'videobuilder.techniques.sound.sound_bridge.bridge_frames'),
    demo=film,
)
