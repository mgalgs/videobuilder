"""Capability: word-timed-captions. A speaker clip plays with its sound, and
the captions underneath follow the words as they're said: the spoken word
in yellow, the keyword ("mornings") in green, two short lines.

    python -m videobuilder preview examples/capabilities/word-timed-captions.py

Everything is synthetic: the subtitles are written here by hand, word by
word, and the clip (a drawn speaker and a generated voice-like tone, see
_speaker.py) is made from those same word times, so picture, sound and
captions agree. LOOP = True by enter/hold/exit: the speaker is silent with
no caption up for the first and last few frames, and sways one full cycle
over the film.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import _speaker  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import Box, text  # noqa: E402

LOOP = True
FPS = 30
SECONDS = 4.0

# The caption file, by hand: one cue per phrase, a time on every word.
SUBS = """WEBVTT

00:00:00.300 --> 00:00:01.600
<00:00:00.300>Honestly,<00:00:00.800> the<00:00:00.950> best<00:00:01.250> part

00:00:01.750 --> 00:00:03.400
<00:00:01.750>is<00:00:01.900> getting<00:00:02.300> my<00:00:02.450> mornings<00:00:02.950> back.
"""
TRACK = vb.captions.parse(SUBS)
KEYWORDS = {'mornings'}
# Each word lasts until the next one starts, less a short gap; the last runs to the cue's end.
WORDS = tuple((w.text, w.start, min(w.end, nxt.start - 0.05) if nxt else w.end)
              for w, nxt in zip(TRACK, list(TRACK)[1:] + [None]))
CLIP_PATH = _speaker.clip(WORDS, SECONDS)
CLIP = vb.Clip(CLIP_PATH)

TITLE_F = _kit.font(22, 600)
CAPTION_F = _kit.font(40, 800)
OVERLAP_OK = {('clip', 'caption')}   # captions sit over the bottom of the footage, as they would on air


def draw(n, cv):
    cv.fill(_kit.BG)
    s = _kit.safe(cv)
    _kit.text_marked(cv, 'title', text.wrap('Word-timed captions', TITLE_F, s.w), TITLE_F, s.x, s.y, _kit.MUTED)
    top = s.y + 52
    clip_box = Box(s.x, top, s.w, s.bottom - top)
    with cv.clip(*clip_box, radius=18):
        pic = CLIP.frame(min(CLIP.frames - 1, CLIP.frame_at(n / FPS)))
        cv.image(pic, *clip_box.cover(*CLIP.size))
    cv.mark('clip', *clip_box)
    vb.captions.draw(cv, TRACK, n / FPS, keywords=KEYWORDS, font=CAPTION_F, safe=clip_box.pad(24))


FILM = vb.Film(draw=draw, fps=FPS, frames=round(SECONDS * FPS), formats=(_kit.FORMAT,), background=_kit.BG,
               sounds=(vb.Sound(CLIP_PATH, at=0, start=0, frames=round(SECONDS * FPS), fade_in_frames=0,
                                fade_out_frames=0),),
               keyframes=(30, 60, 80))

if __name__ == '__main__':
    vb.main(__file__)
