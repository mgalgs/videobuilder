"""Synthetic footage with its own sound, for the demos that need a clip to
play: a drawn speaker whose mouth moves with a generated voice-like tone,
rendered once by videobuilder itself to an MP4 (picture and AAC sound) and
cached in the temp dir. Nothing recorded, downloaded or copyrighted.

`clip(words, seconds)` takes the words as (text, start, end) in seconds on the
clip's own clock (a caption track's words fit as they are), so the mouth, the
sound and any captions made from the same words all agree by construction.

The showcase uses it too (examples/showcase_scenes/voice.py).
"""
import array
import hashlib
import io
import math
import os
import re
import tempfile
import wave
from pathlib import Path

import videobuilder as vb

RATE = 48000
FPS = 30
SIZE = (640, 360)
_SOURCE = Path(__file__).read_bytes()


# ---- the voice: a buzz per syllable, its loudness the mouth's opening ----
def _syllables(word):
    return max(1, len(re.findall(r'[aeiouy]+', word.lower().rstrip('e') or word.lower())))


def level(words, t):
    """How open the mouth is (and how loud the voice) at `t` seconds, 0..1:
    one rounded bump per syllable of the word being spoken."""
    for text, a, z in words:
        if a <= t < z:
            n = _syllables(text)
            u = (t - a) / (z - a) * n
            return math.sin(math.pi * (u - int(u))) ** 0.6
    return 0.0


def voice(words, seconds):
    """Mono 16-bit samples: a gliding fundamental with a few harmonics whose
    mix changes per syllable, like vowels, falling in pitch over each phrase."""
    n = int(seconds * RATE)
    out = [0.0] * n
    for wi, (text, a, z) in enumerate(words):
        syl = _syllables(text)
        i0, i1 = int(a * RATE), min(n, int(z * RATE))
        phase = 0.0
        for i in range(i0, i1):
            t = i / RATE
            u = (t - a) / (z - a)
            k = min(syl - 1, int(u * syl))
            env = level(((text, a, z),), t)
            f0 = 150 + 30 * math.sin(1.7 * wi + 2.3 * k) - 18 * u
            phase += 2 * math.pi * f0 / RATE
            vowel = (1.7 * wi + 3.1 * k) % 3   # which harmonic gets the formant
            s = 0.0
            for h in range(1, 6):
                s += math.sin(h * phase) / h * (1.8 if abs(h - 2 - vowel) < 0.75 else 1.0)
            out[i] += env * s
    peak = max(1e-9, max(abs(v) for v in out))
    return array.array('h', (int(v / peak * 0.6 * 32767) for v in out))


# ---- the picture: a speaker at a desk mic, in a lit studio ----
SKIN = '#e8b48f'
HAIR = '#3b2a26'
TOP = '#4fc3b0'
WALL = '#2b3550'
SPOT = '#55648c'


def speaker(cv, words, t, seconds):
    """One frame of the speaker at `t` seconds, filling `cv`; the sway is one
    cycle over the clip's `seconds`, so a clip played whole loops cleanly."""
    w, h = cv.width, cv.height
    u = h / 360
    cv.fill(WALL)
    for i in range(6):   # a soft spotlight on the back wall
        r = (230 - 30 * i) * u
        cv.rect(w * 0.5 - r, h * 0.42 - r, 2 * r, 2 * r, SPOT, radius=r, alpha=0.12)
    cx = w * 0.5 + 6 * u * math.sin(2 * math.pi * t / seconds)   # a little sway
    cy = h * 0.43
    cv.rect(cx - 120 * u, cy + 70 * u, 240 * u, 200 * u, TOP, radius=70 * u)   # shoulders
    cv.rect(cx - 22 * u, cy + 40 * u, 44 * u, 50 * u, SKIN, radius=12 * u)       # neck
    hr = 66 * u
    cv.rect(cx - hr, cy - hr - 6 * u, 2 * hr, 2 * hr + 10 * u, HAIR, radius=hr)  # hair behind the face
    cv.rect(cx - hr * 0.9, cy - hr * 0.8, 1.8 * hr, 1.85 * hr, SKIN, radius=hr * 0.9)
    blink = any(abs(t - b) < 0.06 for b in (0.9, 2.7, 4.6))
    for side in (-1, 1):
        ex = cx + side * 24 * u
        if blink:
            cv.rect(ex - 8 * u, cy - 2 * u, 16 * u, 3 * u, HAIR, radius=1.5 * u)
        else:
            cv.rect(ex - 6 * u, cy - 8 * u, 12 * u, 14 * u, HAIR, radius=6 * u)
    m = level(words, t)
    mw, mh = (34 - 8 * m) * u, (4 + 22 * m) * u
    cv.rect(cx - mw / 2, cy + 34 * u - mh / 2, mw, mh, '#7a2e2e', radius=min(mw, mh) / 2)
    # the desk and a mic on a short stand, in front of the speaker
    cv.rect(0, h * 0.86, w, h * 0.14, '#1b2033')
    mx = w * 0.5 + 92 * u
    cv.rect(mx - 3 * u, h * 0.70, 6 * u, h * 0.17, '#9397a1')
    cv.rect(mx - 15 * u, h * 0.58, 30 * u, 50 * u, '#20232b', radius=15 * u)
    # a level meter in the corner, driven by the same voice
    for i in range(8):
        on = m * 8 > i
        cv.rect(w - 34 * u, h - 40 * u - i * 14 * u, 18 * u, 10 * u, '#ffd23f' if on else '#3a4363', radius=2 * u)


def clip(words, seconds, size=SIZE):
    """The path of an MP4 of the speaker saying `words` (text, start, end)
    over `seconds`, with its voice as the sound. Built once and cached."""
    words = tuple((str(x), float(a), float(z)) for x, a, z in words)
    key = hashlib.sha1(_SOURCE + repr((words, seconds, size)).encode()).hexdigest()[:12]
    path = os.path.join(tempfile.gettempdir(), f'videobuilder-speaker-{key}.mp4')
    if os.path.exists(path):
        return path
    tmp = f'{path}.{os.getpid()}'
    with wave.open(tmp + '.wav', 'wb') as wv:
        wv.setnchannels(1)
        wv.setsampwidth(2)
        wv.setframerate(RATE)
        wv.writeframes(voice(words, seconds).tobytes())
    film = vb.Film(lambda n, cv: speaker(cv, words, n / FPS, seconds), fps=FPS, frames=round(seconds * FPS),
                   formats=(vb.Format('speaker', *size),), audio=vb.Audio(tmp + '.wav', loudness=None))
    from videobuilder.render import render
    render(film, tmp + '.mp4', jobs=1, crf=20, log=io.StringIO())
    os.replace(tmp + '.mp4', path)
    os.remove(tmp + '.wav')
    return path
