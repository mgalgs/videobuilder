"""Silence drop: everything on the soundtrack stops dead for a beat, then the
next sound lands into the empty air and hits harder for it."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _piece(s, at, start, frames, fade_in, fade_out):
    return vb.Sound(s.path, at=at, start=start, frames=frames, gain_db=s.gain_db, fade_in_frames=fade_in,
                    fade_out_frames=fade_out, ducks=s.ducks)


def silence_drop(sounds, at, frames, fps=30, fade_frames=1):
    """`sounds` (any `vb.Sound`s: a music bed placed as a Sound with
    `ducks=False`, `vb.sfx` effects) with frames `at` to `at + frames` cut
    to silence. A sound playing into the gap stops at `at` (a `fade_frames`
    ramp, so the cut doesn't click); one still playing after it resumes at
    `at + frames` from where its file would be had it kept going, so a
    track comes back on its beat. Sounds clear of the gap are returned as
    they were. Put the hit that answers the silence on `at + frames`, after
    this, so it isn't cut too:

        music = vb.Sound('assets/music.wav', at=0, start=0, frames=FILM_FRAMES, ducks=False)
        sounds = silence_drop((music, *effects), at=DROP, frames=18) + (vb.sfx.sound('pro_impact/deep', at=DROP + 18),)
    """
    end, out = at + frames, []
    for s in sounds:
        first, last = s.at, s.at + s.frames
        if last <= at or first >= end:
            out.append(s)
            continue
        if (at - first) / fps + min(s.start, 0) > 0.5 / fps:   # more than a sliver plays before the cut
            out.append(_piece(s, first, s.start, at - first, s.fade_in_frames, fade_frames))
        if last > end:
            out.append(_piece(s, end, s.start + (end - first) / fps, last - end, fade_frames,
                              s.fade_out_frames))
    return tuple(out)


# ---- the demo: a little beat, cut to silence, answered by a hit ----
BEAT = 8                      # frames per beat (about 112 bpm)
DROP, GAP = 48, 16            # the silence: frames 48 to 64
HIT = DROP + GAP
END = round(demo.SECONDS * demo.FPS)
NOTES = ('G5', 'A5', 'G5', 'G5', 'A5', 'A5')
BARS = 11


def _beat():
    out = []
    for i, n in enumerate(range(0, END, BEAT)):
        if i % 2 == 0:
            out.append(vb.sfx.sound('fit/click/floss_lid', at=n, align='onset', gain_db=-4))
            out.append(vb.sfx.sound('pro_notify/ding_2045', at=n, align='onset', note=NOTES[i // 2 % len(NOTES)],
                                    gain_db=-12))
        else:
            out.append(vb.sfx.sound('fit/click/floss_lid', at=n, align='onset', gain_db=-12))
    return out


def _sounds():
    hit = vb.sfx.sound('pro_impact/short', at=HIT, gain_db=-2)
    return silence_drop(_beat(), DROP, GAP, demo.FPS) + (hit,)


def _level(t, k=0):
    """How loud the demo's soundtrack is at frame `t` (0..1), bar `k` jittered."""
    if DROP <= t < HIT:
        return 0.0
    since = t % BEAT
    beat = int(t // BEAT)
    accent = 1.0 if beat % 2 == 0 else 0.6
    shape = 0.55 + 0.45 * math.sin(k * 1.7 + beat * 2.3) ** 2
    level = 0.15 + 0.6 * accent * shape * math.exp(-since / 3.0)
    if t >= HIT:
        level += 1.1 * math.exp(-(t - HIT) / 9.0) * (0.7 + 0.3 * math.cos(k - BARS // 2))
    return min(1.0, level)


def _draw(n, cv):
    silent, hit = DROP <= n < HIT, n >= HIT
    cx, cy = demo.W / 2, demo.H * 0.36
    # the level bars
    bw, gap = 28, 13
    x0 = cx - (BARS * bw + (BARS - 1) * gap) / 2
    for k in range(BARS):
        h = max(4, 190 * _level(n, k))
        color = demo.ACCENT if hit else demo.TEAL
        cv.rect(x0 + k * (bw + gap), cy - h / 2, bw, h, color, radius=bw / 2,
                alpha=0.35 if silent else 1.0)
    # the state, under the bars
    label = 'silence' if silent else ('HIT' if hit else 'music')
    f = demo.mono(22 if not hit else 30, 700 if hit else 500)
    w, h = vb.text.block_size([label], f)
    vb.text.draw(cv, [label], f, cx - w / 2, cy + 112, demo.INK if not silent else demo.MUTED)
    # the waveform strip: the whole soundtrack, the gap flat, a playhead
    left, right, base, amp = 60, demo.W - 60, demo.H * 0.84, 34
    step = 4
    for x in range(left, right, step):
        t = (x - left) / (right - left) * END
        a = max(1, amp * _level(t, x // step))
        played = t <= n
        cv.line(x, base - a, x, base + a, demo.INK if played else demo.MUTED, width=2,
                alpha=0.9 if played else 0.35)
    px = left + (right - left) * n / END
    cv.line(px, base - amp - 10, px, base + amp + 10, demo.ACCENT, width=2)
    # the hit's flash
    if hit:
        cv.fill('#ffffff', alpha=0.55 * math.exp(-(n - HIT) / 2.5))


CAPABILITY = Capability(
    id='silence-drop',
    name='Silence drop',
    family='sound',
    group='Music',
    aliases=('drop to silence', 'sudden silence', 'dramatic pause'),
    definition='The soundtrack cuts out completely for a brief moment so that the sound which follows, '
               'often a hit on a reveal, lands with extra force.',
    phrasings=('kill the music for a second right before the reveal',
               'go dead quiet for a beat, then slam back in',
               'pull all the audio out just before the big moment'),
    related=('sub-drop', 'smash-cut', 'glitch-sound', 'impact-hit', 'ducking', 'sound-bridge'),
    api=('videobuilder.capabilities.sound.silence_drop.silence_drop', 'videobuilder.sfx.sound'),
    demo=lambda: demo.film(_draw, sounds=_sounds()),
)
