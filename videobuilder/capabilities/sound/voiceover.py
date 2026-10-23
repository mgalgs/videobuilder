"""Voiceover: an unseen narrator speaks over the picture. videobuilder already
has it as `vb.speech`: a script voiced once with `python -m videobuilder say`,
loaded with `vb.speech.load`, placed on the film with `Narration.sound(at=)`
(it ducks the music, `vb.Audio(duck_db=)`), its captions from
`Narration.track_at`. So this entry only names it and demos it:

    VOICE = vb.speech.load('assets/narration.wav')
    FILM = vb.Film(..., audio=vb.Audio('assets/music.wav', duck_db=-12), sounds=(VOICE.sound(at=15),))

The demo can't ship a voice (a capability's demo takes its sound from the
bundled effects pack), so its narrator is a stand-in: two lines of
syllable blips at a speaking pace over a slow push on a photo, with the
narrator's tag, the words lighting as they're "said", and the voice's lane.
Under it, a soft kalimba bed ducked by `DUCK_DB` while each line is spoken:
heard full before the first line, between the two and after the last, with
a thin music lane under the voice's whose level sinks under each line.
"""
import math

import videobuilder as vb

from ... import speech
from .. import _demo as demo
from ..schema import Capability

# the narrator's two lines: (first frame, words as syllables)
LINES = ((10, (('Ev', 'ery'), ('place',), ('has',), ('a',), ('sto', 'ry.'))),
         (58, (('This',), ('one',), ('starts',), ('qui', 'et', 'ly.'))))
SECONDS = 3.6                # a little longer than the kit's 3 s, so the bed is heard up between and after the lines
STEP = 4                     # frames per syllable, about seven a second
WORD_GAP = 1                 # extra frames between words
VOICE = 'pro_notify/ding_2045'
PITCH = ('G5', 'A5', 'G5', 'G5', 'A5', 'G5', 'G5', 'A5')  # a speaking contour, rising on stresses
BED = 'pluck/kalimba_soft'   # the stand-in music: a slow arpeggio an octave and more under the voice
BED_NOTES = ('C4', 'G4', 'E4', 'G4')
BED_EVERY = 6                # frames between the bed's notes
DUCK_DB = -14                # how far the bed sinks under each line
DUCK_IN, RELEASE = 2, 5      # frames the bed takes to sink before a line, and to come back up after it
LANE_Y, LANE_AMP = 417, 28   # the voice's lane: its baseline and loudest swing
MUSIC_Y, MUSIC_H = 506, 34   # the music's lane under it: its baseline and full-level height
X0, X1 = 150, demo.W - 70
TOTAL = round(SECONDS * demo.FPS)


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


def _duck_span(li):
    """(first frame, frames) of the span line `li` ducks the bed over: from
    `DUCK_IN` frames before its first syllable to `RELEASE` past its last."""
    a, b = _line_span(li)
    return a - DUCK_IN, b + RELEASE - (a - DUCK_IN)


def _music_db(n):
    """The bed's gain in dB at frame `n`, as the render's duck envelope has
    it: 0, ramping down to `DUCK_DB` over each line's span edges."""
    env = 0.0
    for li in range(len(LINES)):
        at, frames = _duck_span(li)
        env = max(env, min(vb.clamp01((n - at) / DUCK_IN), vb.clamp01((at + frames - n) / RELEASE)))
    return DUCK_DB * env


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
    s = max(demo.W / img.w, demo.H / img.h) * (1.04 + 0.08 * n / TOTAL)
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
            demo.word(cv, t, x + w / 2, demo.H * 0.6, font=f, color=demo.INK if said else demo.MUTED,
                      alpha=1.0 if said else 0.55)
            x += w + space
        cv.mark('line', demo.W * 0.15, demo.H * 0.6 - 45, demo.W * 0.7, 90)

    # the mixer: the voice's waveform, and under it the music's level sinking while the voice plays
    fx = lambda fr: X0 + (X1 - X0) * fr / TOTAL   # noqa: E731
    top, bottom = LANE_Y - LANE_AMP - 8, MUSIC_Y + 8
    cv.rect(40, top, X1 - 40 + 30, bottom - top, demo.BG, radius=16, alpha=0.85)
    label = demo.font(20, 700)
    vb.text.draw(cv, ['voice'], label, 58, LANE_Y - 13, demo.ACCENT)
    vb.text.draw(cv, ['music'], label, 58, MUSIC_Y - MUSIC_H / 2 - 12, demo.TEAL)
    cv.line(X0, LANE_Y, X1, LANE_Y, demo.LINE, width=2)
    for i in range(TOTAL):
        amp = LANE_AMP * _level(i) * (0.65 + 0.35 * abs(math.sin(i * 2.1)))
        if amp > 1.5:
            cv.line(fx(i), LANE_Y - amp, fx(i), LANE_Y + amp, demo.ACCENT if i <= n else demo.MUTED,
                    width=4, alpha=0.95 if i <= n else 0.35)
    cv.mark('voice lane', X0, LANE_Y - LANE_AMP, X1 - X0, 2 * LANE_AMP)
    cv.line(X0, MUSIC_Y, X1, MUSIC_Y, demo.LINE, width=2)
    gain = lambda fr: 10 ** (_music_db(fr) / 20)   # noqa: E731
    for i in range(TOTAL - 1):
        heard = i < n
        cv.line(fx(i), MUSIC_Y - MUSIC_H * gain(i), fx(i + 1), MUSIC_Y - MUSIC_H * gain(i + 1),
                demo.TEAL if heard else demo.MUTED, width=4 if heard else 2, alpha=1 if heard else 0.5)
    cv.mark('music lane', X0, MUSIC_Y - MUSIC_H, X1 - X0, MUSIC_H)
    cv.line(fx(n), top + 4, fx(n), bottom - 4, demo.INK, width=3)


def film():
    # stand-in voice: one short tuned blip per syllable, at a speaking pace and contour
    # (`through`: an effect dips with the music, and this one is the voice the music dips under)
    sounds = tuple(vb.sfx.sound(VOICE, at=f, align='onset', note=PITCH[k % len(PITCH)], dur=0.11, gain_db=-8,
                                through=True)
                   for k, (f, _, _) in enumerate(SYLLABLES))
    # A real narration is one plain `vb.Sound` per line, and the music ducks under it; the blips are effects,
    # which don't, so each line gets an inaudible plain Sound over its span to duck the bed as a voice would.
    key = sounds[0].path
    keys = tuple(vb.Sound(key, at=at, start=0.0, frames=frames, gain_db=-90, fade_in_frames=DUCK_IN,
                          fade_out_frames=RELEASE)
                 for at, frames in map(_duck_span, range(len(LINES))))
    # the bed: its "music" file the first note, the rest of the arpeggio effects that sink with it
    # (a pack without the kalimba plays the voice's ding at its own pitch instead)
    try:
        bed, tune = vb.sfx.get(BED), BED_NOTES
    except ValueError:
        bed, tune = vb.sfx.get(VOICE), (None,)
    music = vb.Audio(bed.take(note=tune[0]).path, gain_db=-15, duck_db=DUCK_DB)
    notes = tuple(bed.sound(at=f, note=tune[i % len(tune)], gain_db=-15, align='onset')
                  for i, f in enumerate(range(0, TOTAL, BED_EVERY)) if i)
    return demo.film(draw, seconds=SECONDS, audio=music, sounds=sounds + keys + notes)


CAPABILITY = Capability(
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
    # Shared with the hand-written `narration` catalog entry (capabilities/__init__.py), so the two
    # can't drift: see speech.narration_settings.
    settings=speech.narration_settings(),
)
