"""Voiceover: an unseen narrator speaks over the picture. videobuilder already
has it as `vb.speech`: a script voiced once with `python -m videobuilder say`,
loaded with `vb.speech.load`, placed on the film with `Narration.sound(at=)`
(it ducks the music, `vb.Audio(duck_db=)`), its captions from
`Narration.track_at`. So this entry only names it and demos it:

    VOICE = vb.speech.load('assets/narration.wav')
    FILM = vb.Film(..., audio=vb.Audio('assets/music.wav', duck_db=-12), sounds=(VOICE.sound(at=15),))

The demo can't ship a voice (a technique's demo takes its sound from the
bundled effects pack), so its narrator is a stand-in: two lines of
syllable blips at a speaking pace over a slow push on a photo, with the
narrator's tag, the words lighting as they're "said", and the voice's lane.
"""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

# the narrator's two lines: (first frame, words as syllables)
LINES = ((10, (('Ev', 'ery'), ('place',), ('has',), ('a',), ('sto', 'ry.'))),
         (50, (('This',), ('one',), ('starts',), ('qui', 'et', 'ly.'))))
STEP = 4                     # frames per syllable, about seven a second
WORD_GAP = 1                 # extra frames between words
VOICE = 'pro_notify/ding_2045'
PITCH = ('G5', 'A5', 'G5', 'G5', 'A5', 'G5', 'G5', 'A5')  # a speaking contour, rising on stresses
LANE_Y = demo.H - 92
X0, X1 = 150, demo.W - 150


def _syllables():
    """Every syllable as (frame, line index, word index), in order."""
    out = []
    for li, (start, words) in enumerate(LINES):
        f = start
        for wi, word in enumerate(words):
            for _ in word:
                out.append((f, li, wi))
                f += STEP
            f += WORD_GAP
    return out


SYLLABLES = _syllables()


def _line_span(li):
    fs = [f for f, l, _ in SYLLABLES if l == li]
    return fs[0], fs[-1] + STEP


def _level(n):
    """The voice's loudness at frame `n`, 0..1: a swell on each syllable."""
    return max((math.exp(-((n - f - 1) / 1.6) ** 2) for f, _, _ in SYLLABLES), default=0.0)


def _mic(cv, x, y, live):
    """A small microphone glyph, its capsule lit while the narrator speaks."""
    color = demo.ACCENT if live > 0.2 else demo.MUTED
    cv.rect(x - 11, y - 30, 22, 38, color, radius=11)
    cv.arc(x, y - 4, 19, 0, math.pi, color, width=4)
    cv.line(x, y + 15, x, y + 26, color, width=4)
    cv.line(x - 11, y + 26, x + 11, y + 26, color, width=4)
    if live > 0.05:
        for k in (1, 2):
            cv.arc(x, y - 12, 26 + 12 * k, -math.pi * 0.3, math.pi * 0.3, demo.ACCENT, width=3,
                   alpha=0.6 * live / k)
            cv.arc(x, y - 12, 26 + 12 * k, math.pi * 0.7, math.pi * 1.3, demo.ACCENT, width=3,
                   alpha=0.6 * live / k)


def draw(n, cv):
    # the picture: a photo on a slow push, nobody on screen talking
    img = demo.photo()
    box = vb.Box(0, 0, demo.W, demo.H)
    s = max(demo.W / img.w, demo.H / img.h) * (1.04 + 0.08 * n / (demo.SECONDS * demo.FPS))
    cv.view(img, box, center=(img.w * 0.5, img.h * 0.47), scale=s)
    cv.rect(0, demo.H * 0.52, demo.W, demo.H * 0.48, '#000000', alpha=0.45)

    # the narrator's tag, top left: who is speaking, off screen
    live = _level(n)
    cv.rect(40, 36, 290, 74, demo.BG, radius=16, alpha=0.85)
    _mic(cv, 102, 80, live)
    demo.word(cv, 'VO  narrator', 228, 73, size=28, color=demo.INK, weight=800)

    # the line being said, each word lighting as its first syllable lands
    for li, (start, words) in enumerate(LINES):
        a, b = _line_span(li)
        if not (a - 4 <= n <= b + 8):
            continue
        f = demo.font(58, 800)
        texts = [''.join(w) for w in words]
        widths = [vb.text.block_size([t], f)[0] for t in texts]
        space = vb.text.block_size(['a a'], f)[0] - 2 * vb.text.block_size(['a'], f)[0]
        x = demo.W / 2 - (sum(widths) + space * (len(texts) - 1)) / 2
        for wi, (t, w) in enumerate(zip(texts, widths)):
            said = next(fr for fr, l, i in SYLLABLES if l == li and i == wi) <= n
            demo.word(cv, t, x + w / 2, demo.H * 0.66, font=f, color=demo.INK if said else demo.MUTED,
                      alpha=1.0 if said else 0.55)
            x += w + space
        cv.mark('line', demo.W * 0.15, demo.H * 0.6, demo.W * 0.7, 90)

    # the voice's lane: its waveform drawn up to the playhead
    total = demo.SECONDS * demo.FPS
    fx = lambda fr: X0 + (X1 - X0) * fr / total   # noqa: E731
    cv.rect(X0 - 30, LANE_Y - 50, X1 - X0 + 60, 100, demo.BG, radius=16, alpha=0.8)
    cv.line(X0, LANE_Y, X1, LANE_Y, demo.LINE, width=2)
    for i in range(0, int(total), 1):
        amp = 38 * _level(i) * (0.65 + 0.35 * abs(math.sin(i * 2.1)))
        if amp > 1.5:
            cv.line(fx(i), LANE_Y - amp, fx(i), LANE_Y + amp, demo.TEAL if i <= n else demo.MUTED,
                    width=5, alpha=0.95 if i <= n else 0.35)
    cv.line(fx(n), LANE_Y - 46, fx(n), LANE_Y + 46, demo.INK, width=3)
    cv.mark('voice lane', X0 - 30, LANE_Y - 50, X1 - X0 + 60, 100)


def film():
    # stand-in voice: one short tuned blip per syllable, at a speaking pace and contour
    sounds = tuple(vb.sfx.sound(VOICE, at=f, align='onset', note=PITCH[k % len(PITCH)], dur=0.11, gain_db=-8)
                   for k, (f, _, _) in enumerate(SYLLABLES))
    return demo.film(draw, sounds=sounds)


TECHNIQUE = Technique(
    id='voiceover',
    name='Voiceover',
    family='sound',
    group='Mixing & editing',
    aliases=('VO', 'narration', 'voice-over', 'off-screen narrator', 'commentary track'),
    definition='A speaker who is never seen talks over the footage, telling the story while the picture '
               'plays and the music sinks underneath the words.',
    phrasings=('have a narrator read this script over the video',
               'add a spoken explanation on top of the footage',
               'put a voice talking us through the shots, with the music dipping under it'),
    related=('pop-on-captions', 'drone-flyover', 'video-clipped-inside-letterforms', 'analog-ghosting',
             'noise-terrain-flyover', 'slide-over-cover'),
    api=('videobuilder.speech.load', 'videobuilder.speech.Narration.sound', 'videobuilder.speech.Narration.track_at',
         'videobuilder.Audio'),
    demo=film,
)
