"""Sonic logo: a brand's few-note melodic signature, played as its logo
appears, each note landing on the frame where a piece of the mark lands.
`sonic_logo` places the notes as tuned sound effects; `note_frames` gives
the same frames to the picture, so the mark builds in time with the tune."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

MOTIF = ('G5', 'C6', 'E6', 'G6')    # a rising arpeggio that lands on the octave: easy to hum back
RHYTHM = (1, 1, 2)                  # gaps between the notes, in steps: two quick, then a breath before the last


def note_frames(at, notes=MOTIF, step=6, rhythm=RHYTHM):
    """The film frame each note of the motif lands on: the first on `at`,
    each next one `rhythm[i]` steps of `step` frames later (`rhythm` repeats
    its last gap when shorter than the motif)."""
    frames, f = [], at
    for i in range(len(notes)):
        frames.append(f)
        f += step * (rhythm[min(i, len(rhythm) - 1)] if rhythm else 1)
    return tuple(frames)


def nearest_note(sound, note):
    """`note` if the tuned `sound` has it, else the nearest note it has."""
    have = vb.sfx.get(sound).notes
    name = vb.sfx.note_name(note)
    return name if name in have else min(have, key=lambda h: abs(_midi(h) - _midi(name)))


_NAMES = ('C', 'Cs', 'D', 'Ds', 'E', 'F', 'Fs', 'G', 'Gs', 'A', 'As', 'B')


def _midi(name):
    """A pack note name ('Cs6') as a MIDI number."""
    return 12 * (int(name[-1]) + 1) + _NAMES.index(name[:-1])


def sonic_logo(at, notes=MOTIF, step=6, rhythm=RHYTHM, sound='pro_notify/ding_2045', gain_db=-8,
               last_gain_db=-4, sting=None, sting_gain_db=-14, sting_dur=1.5, fps=30):
    """The motif as tuned sound effects for `vb.Film(sounds=...)`: each of
    `notes` (names such as 'C6') played on `sound` at `note_frames(at, ...)`,
    onset on its frame, the last one a little louder. A note `sound` doesn't
    have plays its nearest. `sting` (a sound id, e.g. 'pro_shimmer/m0')
    starts with the last note so the signature rings out. Returns a tuple of `Sfx`."""
    frames = note_frames(at, notes, step, rhythm)
    out = [vb.sfx.sound(sound, at=f, note=nearest_note(sound, nt), align='onset', fps=fps,
                        gain_db=last_gain_db if i == len(notes) - 1 else gain_db)
           for i, (f, nt) in enumerate(zip(frames, notes))]
    if sting:
        out.append(vb.sfx.sound(sting, at=frames[-1], align='onset', dur=sting_dur, gain_db=sting_gain_db, fps=fps))
    return tuple(out)


# ---- the demo: a four-bar mark, one bar per note, its height the note's pitch ----
AT, STEP = 18, 7
FRAMES = note_frames(AT, step=STEP)
BRAND = 'LUMEN'


HEIGHT = (0.42, 0.58, 0.74, 1.0)   # each bar as tall as its note is high


def draw(n, cv):
    cx, base = demo.W / 2, demo.H / 2 + 40
    bw, gap, tall = 46, 26, 230
    x0 = cx - (len(MOTIF) * bw + (len(MOTIF) - 1) * gap) / 2
    lock = demo.phase(n, (FRAMES[-1] + 4) / demo.FPS, (FRAMES[-1] + 22) / demo.FPS)
    rise = vb.ease_out_quint(lock)
    for i, (f, nt) in enumerate(zip(FRAMES, MOTIF)):
        t = (n - f) / demo.FPS
        x = x0 + i * (bw + gap)
        if t < 0:
            cv.rect(x, base - 8, bw, 8, demo.LINE, radius=4)        # a slot waiting for its note
            continue
        h = tall * HEIGHT[i] * vb.ease_out_back(vb.clamp01(t / 0.22))
        color = demo.ACCENT if i == len(MOTIF) - 1 else demo.TEAL
        cv.rect(x, base - h - 40 * rise, bw, h, color, radius=bw / 2)
        if t < 0.6:                                                  # the note's ring, rising off the bar
            k = t / 0.6
            r = bw * 0.6 + 70 * vb.ease_out_quint(k)
            cv.arc(x + bw / 2, base - h - 40 * rise, r, 0, math.tau, color, width=4, alpha=(1 - k) * 0.8)
    demo.word(cv, BRAND, cx, base + 70 - 40 * rise + 30 * (1 - rise), size=72, alpha=rise)
    ln = vb.ease_out_quint(demo.phase(n, (FRAMES[-1] + 10) / demo.FPS, (FRAMES[-1] + 30) / demo.FPS))
    if ln:
        demo.word(cv, '♪  ' + '  '.join(m[:-1] for m in MOTIF), cx, demo.H - 90, size=30,
                  color=demo.MUTED, font=demo.mono(30), alpha=ln)


def build():
    return demo.film(draw, sounds=sonic_logo(AT, step=STEP))


CAPABILITY = Capability(
    id='sonic-logo',
    name='Sonic logo',
    family='sound',
    group='Music',
    aliases=('audio logo', 'sound logo', 'audio signature', 'sonic mnemonic', 'jingle'),
    definition='A brand mark is paired with a short, recognisable run of notes that plays as the logo '
               'appears, each note landing as part of the mark falls into place.',
    phrasings=('give the logo its own little tune when it shows up',
               'a few signature notes that play with the brand reveal',
               'make the logo end card sound like us, like a musical tag'),
    related=('logo-sting', 'sound-reactive-radial-shape', 'whoosh', 'logo-build-on-reveal',
             'logo-mask-wipe-reveal', 'sound-bridge'),
    api=('videobuilder.capabilities.sound.sonic_logo.sonic_logo',
         'videobuilder.capabilities.sound.sonic_logo.note_frames',
         'videobuilder.sfx.sound'),
    demo=build,
)
