"""Capability: narration. The fox says one short line in a generated voice,
the captions under it follow the phrases, and its mouth flaps with the
voice, all from one committed WAV.

    python -m videobuilder preview examples/capabilities/narration.py

The voice was made once with `python -m videobuilder say` from the script
beside it (examples/assets/narration/fox.txt), which wrote fox.wav, fox.vtt
(a cue per phrase) and fox.json; rendering only reads those files. The
mouth is `vb.speech.mouth`: the voice's loudness per frame, open near each
syllable's peak, never for less than two frames.

LOOP = True by enter/hold/exit: the fox stands silent on its idle pose with
no caption up for the first and last frames, and breathes two whole periods.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import Box, text  # noqa: E402

LOOP = True
FPS = 30
TOTAL = 120                  # 4.0 s
AT = 15                      # the voice starts half a second in

VOICE = vb.speech.load(_kit.ASSETS / 'narration' / 'fox.wav')
TRACK = VOICE.track_at(AT, FPS)
MOUTH = VOICE.mouth(FPS, at=AT, frames=TOTAL)
BLINKS = {7, 8, 105, 106}    # only where the voice is silent, so a blink never cuts a word

FOX_DIR = _kit.ASSETS / 'fox'
FOX = vb.Puppet({name: FOX_DIR / f'{name}.png' for name in ('idle', 'talk', 'blink')}, height=390)
GROUND_Y = 530
BREATH = 60

TITLE_F = _kit.font(32, 700)
CAPTION_F = _kit.font(34, 750)


def pose_at(n):
    if MOUTH[n]:
        return 'talk'
    return 'blink' if n in BLINKS else 'idle'


def draw(n, cv):
    cv.fill(_kit.BG)
    s = _kit.safe(cv)
    _kit.text_marked(cv, 'title', text.wrap('Narration', TITLE_F, s.w), TITLE_F, s.x, s.y, _kit.INK)
    cv.line(s.x + 80, GROUND_Y, s.right - 80, GROUND_Y, _kit.LINE, width=2)
    sx, sy = FOX.breath(n, BREATH)
    FOX.draw(cv, pose_at(n), s.cx, GROUND_Y, sx=sx, sy=sy, mark='fox')
    vb.captions.draw(cv, TRACK, n / FPS, font=CAPTION_F, safe=Box(s.x, GROUND_Y + 24, s.w, s.bottom - GROUND_Y - 24),
                     position='middle', color=_kit.INK, box=None)


FILM = vb.Film(draw=draw, fps=FPS, frames=TOTAL, formats=(_kit.FORMAT,), background=_kit.BG,
               sounds=(VOICE.sound(at=AT, fps=FPS),),
               keyframes=((10, 'silent'), (20, 'hi'), (24, 'there'), (50, 'fox'), (64, 'and now'),
                          (88, 'talk'), (112, 'silent')))

if __name__ == '__main__':
    vb.main(__file__)
