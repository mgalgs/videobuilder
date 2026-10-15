"""Capability: footage-with-sound. A music bed plays; a speaker clip comes
on screen and plays with its own sound while the music dips under it, then
the clip goes and the music comes back up. Two meters under the picture
show the two levels, so the dip can be seen as well as heard.

    python -m videobuilder preview examples/capabilities/footage-with-sound.py

The clip is synthetic (a drawn speaker and a generated voice-like tone, see
_speaker.py), cut in with `vb.footage` so its picture and its `Sound` start
at the same source second. LOOP = True by enter/hold/exit: music alone, no
clip on screen, for the first and last beat.
"""
import hashlib
import os
import sys
import tempfile
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import _speaker  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import Box, text  # noqa: E402

LOOP = True
BPM = 120
BEATS = 8   # 4.0 s
GRID = _kit.grid(bpm=BPM)
TIMELINE = vb.Timeline(GRID, [vb.Segment('music', 0, 2), vb.Segment('clip', 2, 6), vb.Segment('music-back', 6, BEATS)],
                       end=BEATS)

# What the speaker says, in seconds on the clip's own clock.
WORDS = (('This', 0.15, 0.4), ('is', 0.45, 0.6), ('the', 0.65, 0.8), ("clip's", 0.85, 1.2),
         ('own', 1.25, 1.5), ('sound.', 1.55, 1.85))
CLIP_SECONDS = 2.0
CLIP_PATH = _speaker.clip(WORDS, CLIP_SECONDS)
CLIP = vb.Clip(CLIP_PATH)
FOOTAGE = vb.footage(TIMELINE, 'clip', start=0.0)
EDGE = 4          # frames: the sound's fade, and the music's dip, at each edge
DUCK_DB = -12

TITLE_F = _kit.font(22, 600)
LABEL_F = _kit.font(22, 600)


def _duck(n):
    """The music's level, 0..1 on the meter: down by DUCK_DB while the clip
    plays, ramping over EDGE frames each side, as the mix does it."""
    a, z = TIMELINE.span('clip')
    t = min(vb.clamp01((n - a) / EDGE), vb.clamp01((z - n) / EDGE))
    return 1 - (1 - 10 ** (DUCK_DB / 20)) * t


def _meter(cv, name, word, level, x, y, w, colour):
    lw = 150
    text.draw(cv, word, LABEL_F, x, y, _kit.INK)
    lh = text.line_height(LABEL_F)
    bx, bw, bh = x + lw, w - lw, 14
    by = y + (lh - bh) / 2
    cv.rect(bx, by, bw, bh, _kit.LINE, radius=bh / 2)
    if level > 0.01:
        cv.rect(bx, by, max(bh, bw * level), bh, colour, radius=bh / 2)
    cv.mark(name, x, y, w, lh)


def draw(n, cv):
    cv.fill(_kit.BG)
    s = _kit.safe(cv)
    _kit.text_marked(cv, 'title', text.wrap('Footage with its own sound', TITLE_F, s.w), TITLE_F, s.x, s.y, _kit.MUTED)

    box = Box(s.x, s.y + 92, s.w, s.w * 9 / 16)
    cv.outline(*box, _kit.LINE, width=2, radius=18)
    seg, f = TIMELINE.at(n)
    if seg.name == 'clip':
        length = TIMELINE.span('clip')[1] - TIMELINE.span('clip')[0]
        p = min(vb.spring_at(f + 3, GRID.fps, **vb.critical(220)),
                vb.ease_out_expo(vb.clamp01((length - 1 - f) / 8)))
        sc = 0.92 + 0.08 * p
        with cv.layer(opacity=vb.clamp01(p), dx=box.cx * (1 - sc), dy=box.cy * (1 - sc), scale=sc):
            with cv.clip(*box, radius=18):
                cv.image(CLIP.frame(CLIP.frame_at(FOOTAGE.seconds_at(n))), *box)
        cv.mark('clip', *box)

    beat = (n % GRID.frames_per_beat) / GRID.frames_per_beat
    music = _duck(n) * (0.86 + 0.14 * (1 - beat) ** 3)   # a little pulse on each beat
    voice = _speaker.level(WORDS, FOOTAGE.seconds_at(n)) if seg.name == 'clip' else 0.0
    _meter(cv, 'music-meter', 'Music', music, s.x, box.bottom + 56, s.w, _kit.ACCENT)
    _meter(cv, 'clip-meter', 'Clip sound', voice, s.x, box.bottom + 104, s.w, _kit.TEAL)


def _music():
    """The placeholder bed, made once by the skill's make_track.py and cached."""
    args = dict(bpm=BPM, beats=BEATS, loop='major', tail=0.6)
    key = hashlib.sha1(repr(sorted(args.items())).encode()).hexdigest()[:12]
    path = os.path.join(tempfile.gettempdir(), f'videobuilder-footage-{key}.wav')
    if not os.path.exists(path):
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'skill' / 'make-a-video' / 'scripts'))
        from make_track import synth
        data = synth(args['bpm'], args['beats'], loop=args['loop'], tail=args['tail'])
        tmp = f'{path}.{os.getpid()}.tmp'
        with wave.open(tmp, 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(48000)
            w.writeframes(data.tobytes())
        os.replace(tmp, path)
    return path


FILM = vb.Film(draw=draw, timeline=TIMELINE, formats=(_kit.FORMAT,), background=_kit.BG,
               audio=vb.Audio(_music(), gain_db=-3, duck_db=DUCK_DB,
                              fade_out_frames=round(0.3 * GRID.frames_per_beat)),
               sounds=(FOOTAGE.sound(CLIP_PATH, fade_in_frames=EDGE, fade_out_frames=EDGE),),
               keyframes=((15, 'music'), (60, 'clip, music dipped'), (105, 'music back')))

if __name__ == '__main__':
    vb.main(__file__)
