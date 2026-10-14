"""Capability: beat-lock. Eight one-beat segments hard-cut on a 120 bpm
grid, each landing on its own number, plus a generated music bed (the only
audio demo in the whole catalog) so the cuts can be heard landing on the
beat, not just seen.

    python -m videobuilder preview examples/capabilities/beat-lock.py

LOOP = True, but not the enter/hold/exit or wrapping-phase pattern used
elsewhere in this catalog: this demo's hero move IS the hard cut, so the
loop point is deliberately just another on-grid hard cut (beat 8 cutting
back to beat 1) rather than a soft fade -- that's a choice, not an
oversight.
"""
import hashlib
import os
import sys
import tempfile
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import text  # noqa: E402

LOOP = True
BPM = 120
BEATS = 8   # 4.0 s at 120 bpm, 15 frames/beat
GRID = _kit.grid(bpm=BPM)
TIMELINE = vb.Timeline(GRID, [vb.Segment(f'beat-{i + 1}', i, i + 1) for i in range(BEATS)], end=BEATS)

TITLE_F = _kit.font(22, 600)
NUMBER_F = _kit.font(168, 700, family=_kit.MONO)

DOT_R = 7
DOT_GAP = 30


def draw(n, cv):
    cv.fill(_kit.BG)
    s = _kit.safe(cv, 64)
    seg, _f = TIMELINE.at(n)
    beat = int(seg.name.split('-')[1])   # 1..8

    _kit.text_marked(cv, 'title', text.wrap('Beat-locked cuts', TITLE_F, s.w), TITLE_F, s.x, s.y, _kit.MUTED)

    num = str(beat)
    nw, nh = text.block_size([num], NUMBER_F)
    text.draw(cv, [num], NUMBER_F, s.cx - nw / 2, s.cy - nh / 2 - 20, _kit.INK)
    cv.mark('number', s.cx - nw / 2, s.cy - nh / 2 - 20, nw, nh)

    row_w = (BEATS - 1) * DOT_GAP + BEATS * 2 * DOT_R
    row_x = s.cx - row_w / 2
    row_y = s.bottom - 2 * DOT_R
    for i in range(BEATS):
        x = row_x + i * (2 * DOT_R + DOT_GAP)
        filled = (i + 1) <= beat
        colour = _kit.ACCENT if filled else _kit.LINE
        cv.rect(x, row_y, 2 * DOT_R, 2 * DOT_R, colour, radius=DOT_R)
        cv.mark(f'tick-{i + 1}', x, row_y, 2 * DOT_R, 2 * DOT_R)


def _music():
    """The placeholder bed, made once by the skill's make_track.py and cached."""
    args = dict(bpm=BPM, beats=BEATS, loop='minor', tail=0.6)
    key = hashlib.sha1(repr(sorted(args.items())).encode()).hexdigest()[:12]
    path = os.path.join(tempfile.gettempdir(), f'videobuilder-beatlock-{key}.wav')
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
               audio=vb.Audio(_music(), gain_db=-3, fade_out_frames=round(0.3 * GRID.frames_per_beat)),
               keyframes=tuple(GRID.b(i) for i in range(BEATS)))

if __name__ == '__main__':
    vb.main(__file__)
