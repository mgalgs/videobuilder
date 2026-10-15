"""A beta tester on camera: a clip with its own sound, the music dipping
under it, and captions following the words as they're said. The clip is
synthetic, the catalog's drawn speaker (examples/capabilities/_speaker.py)
saying the words of the caption file below with a generated voice-like
tone; its `Sound` and the music's dip are set up in examples/showcase.py."""
import sys

import videobuilder as vb
from videobuilder import Box

from . import kit
from .kit import BG, CARD, FPS, pick

sys.path.insert(0, str(kit.HERE.parent / 'capabilities'))
import _speaker  # noqa: E402

SECONDS = 2.5   # the shot's length: 5 beats
SUBS = """WEBVTT

00:00:00.200 --> 00:00:02.200
<00:00:00.200>Lumen<00:00:00.600> gave<00:00:00.880> me<00:00:01.040> my<00:00:01.220> mornings<00:00:01.780> back.
"""
TRACK = vb.captions.parse(SUBS)
KEYWORDS = {'mornings'}
WORDS = tuple((w.text, w.start, min(w.end, nxt.start - 0.04) if nxt else w.end)
              for w, nxt in zip(TRACK, list(TRACK)[1:] + [None]))
CLIP_PATH = _speaker.clip(WORDS, SECONDS, size=(1280, 720))
CLIP = vb.Clip(CLIP_PATH)


def window(st):
    """The clip's window: 16:9 filling the content height in 16:9, a tall crop in 9:16."""
    c = st.content
    w, h = (c.h * 16 / 9, c.h) if st.wide else (c.w, min(c.h, c.w * 5 / 4))
    return Box(c.cx - w / 2, c.cy - h / 2, w, h)


def voice(cv, s, st):
    cv.fill(BG)
    box = window(st)
    p = kit.spring(s.f, -4)
    sc = 0.96 + 0.04 * min(1.0, p)
    with kit.scaled(cv, box.cx, box.cy, sc):
        cv.shadow(*box, radius=24, dy=16, blur=40, color=(0, 0, 0, 0.5))
        cv.rect(*box, CARD, radius=24)
        with cv.clip(*box, radius=24):
            cv.image(CLIP.frame(min(CLIP.frames - 1, CLIP.frame_at(s.f / FPS))), *box.cover(*CLIP.size))
    cv.mark('footage', *box)
    vb.captions.draw(cv, TRACK, s.f / FPS, keywords=KEYWORDS, font=kit.font(pick(st, 48, 44), 800),
                     safe=box.pad(pick(st, 32, 28)))


SCENES = {'voice': voice}
