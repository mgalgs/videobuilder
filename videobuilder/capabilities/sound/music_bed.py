"""Music bed: a quiet, steady piece of music that runs under the whole film,
setting the mood while the sound effects (or a voice) sit clearly on top.

Built from the sound-effects pack's tuned kalimba, so no music file is needed:
a looping chord arpeggio, every note its own placed sound, kept well below
the effects."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

NAMES = ('C', 'Cs', 'D', 'Ds', 'E', 'F', 'Fs', 'G', 'Gs', 'A', 'As', 'B')
# One chord per beat, low to high: C, A minor, F, G.
CHORDS = (('C4', 'G4', 'E5'), ('A4', 'E5', 'C5'), ('F4', 'C5', 'A4'), ('G4', 'D5', 'B4'))


def _midi(note):
    """A note's MIDI number: 'C4' is 60."""
    name = vb.sfx.note_name(note)              # 'C#4' -> 'Cs4'
    pitch, octave = name.rstrip('-0123456789'), int(name.lstrip('ABCDEFGs'))
    return 12 * (octave + 1) + NAMES.index(pitch)


def bed_notes(start, frames, bpm=120, chords=CHORDS, per_beat=2, fps=30):
    """The bed's notes as `(frame, note)` pairs from frame `start` for `frames`
    frames: `per_beat` notes a beat, stepping through each beat's chord, one
    chord a beat, the progression looping. Visuals can key off the same list."""
    step = fps * 60 / bpm / per_beat
    out, i = [], 0
    while round(i * step) < frames:
        chord = chords[(i // per_beat) % len(chords)]
        out.append((start + round(i * step), chord[i % len(chord)]))
        i += 1
    return out


def music_bed(start, frames, bpm=120, chords=CHORDS, gain_db=-18.0, voice='pluck/kalimba_soft', per_beat=2,
              fps=30):
    """A music bed as a tuple of `vb.sfx` sounds for a film's `sounds`: the
    `bed_notes` arpeggio played on `voice` (a tuned sound), each note landing
    by its onset, all at `gain_db`, low enough that effects at -10 to -4 dB
    sit clearly above it. A note `voice` lacks plays as its nearest one. Lay
    it from frame 0 for the film's whole length."""
    effect = vb.sfx.get(voice)

    def nearest(note):
        return min(effect.notes, key=lambda n: abs(_midi(n) - _midi(note)))

    return tuple(effect.sound(f, fps, align='onset', gain_db=gain_db, note=nearest(note))
                 for f, note in bed_notes(start, frames, bpm, chords, per_beat, fps))


FRAMES = round(demo.SECONDS * demo.FPS)
POPS = (round(0.9 * demo.FPS), round(1.9 * demo.FPS))   # the two effects heard over the bed
NOTES = bed_notes(0, FRAMES)
LEFT, RIGHT = 190, demo.W - 50
SFX_Y, BED_Y = 320, 445                                 # lane centres


def _x(f):
    return LEFT + (RIGHT - LEFT) * f / (FRAMES - 1)


def _label(cv, text, y, color):
    f = demo.mono(16, 700)
    vb.text.draw(cv, [text], f, 50, y - vb.text.block_size([text], f)[1] / 2, color)


def draw(n, cv):
    # The foreground: a card pops in on each effect.
    for i, at in enumerate(POPS):
        if n > at:
            p = demo.phase(n, at / demo.FPS, at / demo.FPS + 0.3)
            demo.card(cv, demo.W / 2 + (i * 2 - 1) * 150, 140, w=180, h=110,
                      color=demo.ACCENT if i == 0 else demo.TEAL, scale=vb.ease_out_back(p))
    # The mix, as two lanes: loud effects above, the low, unbroken bed under them.
    _label(cv, 'SFX', SFX_Y, demo.INK)
    _label(cv, 'MUSIC BED', BED_Y, demo.TEAL)
    cv.line(LEFT, SFX_Y, RIGHT, SFX_Y, demo.LINE, width=2)
    cv.rect(LEFT, BED_Y - 34, RIGHT - LEFT, 68, demo.TEAL, radius=10, alpha=0.12)
    for at in POPS:
        lit = n >= at
        cv.rect(_x(at) - 6, SFX_Y - 55, 12, 110, demo.ACCENT, radius=6, alpha=1.0 if lit else 0.3)
    for k in range(int((RIGHT - LEFT) / 8)):
        x = LEFT + 4 + k * 8
        f = (x - LEFT) / (RIGHT - LEFT) * (FRAMES - 1)
        since = min((f - nf for nf, _ in NOTES if nf <= f), default=0)
        h = 7 + 18 * math.exp(-since / 6) * (0.75 + 0.25 * math.sin(k * 1.7))
        cv.rect(x - 2.5, BED_Y - h, 5, 2 * h, demo.TEAL, radius=2.5, alpha=0.9 if f <= n else 0.3)
    x = _x(n)
    cv.line(x, SFX_Y - 75, x, BED_Y + 50, demo.INK, width=2)
    # The bed's level breathes with its notes but never stops.
    since = min(n - nf for nf, _ in NOTES if nf <= n)
    demo.dot(cv, x, BED_Y, r=7 + 5 * math.exp(-since / 5), color=demo.TEAL)
    cv.mark('playhead', x - 1, SFX_Y - 75, 2, BED_Y - SFX_Y + 125)


def _bed_voice():
    # The kalimba when the pack has it; a pack without it (the tests' small one) has this ding.
    try:
        vb.sfx.get('pluck/kalimba_soft')
        return 'pluck/kalimba_soft'
    except ValueError:
        return 'pro_notify/ding_2045'


def film():
    hits = tuple(vb.sfx.sound('pro_impact/short', at=at, gain_db=-6) for at in POPS)
    return demo.film(draw, sounds=music_bed(0, FRAMES, voice=_bed_voice()) + hits)


CAPABILITY = Capability(
    id='music-bed',
    name='Music bed',
    family='sound',
    group='Music',
    aliases=('background music', 'underscore', 'bed track'),
    definition='A soft, continuous piece of music plays beneath the entire film, setting its mood '
               'while the effects and any voice stay clearly louder on top.',
    phrasings=('put some quiet music underneath the whole thing',
               'add a background track that sets the mood but stays out of the way',
               'I want gentle music running under the sound effects'),
    related=('ambience', 'ducking', 'sound-bridge', 'audio-waveform-bars', 'stereo-panning',
             'aurora-gradient-background'),
    api=('videobuilder.capabilities.sound.music_bed.music_bed',
         'videobuilder.capabilities.sound.music_bed.bed_notes',
         'videobuilder.Audio'),
    demo=film,
)
