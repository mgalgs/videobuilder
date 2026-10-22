"""Musical sting: a quick run of pickup notes that lands on a chord, the chord
on the frame of the moment it punctuates (a reveal, a punchline, an ending).
Built from the sound-effects bank's tuned sounds, one `vb.sfx.sound` per note."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

PICKUP = ('G5', 'A5', 'B5')
CHORD = ('C6', 'E6', 'G6')


def sting_frames(at, pickup=PICKUP, gap=5):
    """The film frame of each pickup note, `gap` frames apart, the last one
    `gap` frames before the chord on `at`."""
    return tuple(at - gap * (len(pickup) - i) for i in range(len(pickup)))


def sting(at, pickup=PICKUP, chord=CHORD, gap=5, voice='pro_notify/ding_2045', gain_db=-10, chord_gain_db=None,
          hit=None, hit_gain_db=-8, fps=30, through=False):
    """A musical sting as a tuple of `vb.sfx` sounds for a film's `sounds`:
    each note of `pickup` struck `gap` frames apart (see `sting_frames`),
    then every note of `chord` together with its peak on frame `at`. `voice`
    is a tuned bank sound (a ding or a pluck such as 'pluck/kalimba_ring');
    `chord_gain_db` defaults to `gain_db`. `hit`, a bank sound id such as
    'pro_impact/short', adds weight under the chord. Pass `pickup=()` for a
    single chord hit."""
    chord_gain_db = gain_db if chord_gain_db is None else chord_gain_db
    notes = [vb.sfx.sound(voice, f, fps=fps, note=nt, gain_db=gain_db, through=through)
             for f, nt in zip(sting_frames(at, pickup, gap), pickup)]
    notes += [vb.sfx.sound(voice, at, fps=fps, note=nt, gain_db=chord_gain_db, through=through) for nt in chord]
    if hit:
        notes.append(vb.sfx.sound(hit, at, fps=fps, gain_db=hit_gain_db, through=through))
    return tuple(notes)


# ---- the demo ----
HIT = 45                       # the chord, at 1.5 s
GAP = 5
TUNE = ('G5', 'G5')            # da-da-DAH: two pickups, landing a step up
LAND = ('A5',)
STAFF_X0, STAFF_X1 = 250, demo.W - 250
STAFF_Y = demo.H / 2 - 20      # the bottom line (E5: the staff reads an octave up)
STEP = 11                      # half a line spacing: one diatonic step
LETTERS = 'CDEFGAB'


def _staff_y(note):
    """Height of a note head on the staff, from its name ('G5', 'A5')."""
    steps = LETTERS.index(note[0]) + 7 * int(note[-1]) - (LETTERS.index('E') + 7 * 5)
    return STAFF_Y - steps * STEP


def _head(cv, x, y, age, color, r=9):
    if age < 0:
        return
    s = vb.ease_out_back(vb.clamp01(age / 6))
    cv.sector(x, y, r * s, 0, 2 * math.pi, color)


def draw(n, cv):
    for i in range(5):
        cv.line(STAFF_X0, STAFF_Y - 2 * STEP * i, STAFF_X1, STAFF_Y - 2 * STEP * i, demo.MUTED, width=2, alpha=0.5)
    xs = [STAFF_X0 + 90 + 85 * i for i in range(len(TUNE) + 1)]
    for x, f, nt in zip(xs, sting_frames(HIT, TUNE, GAP), TUNE):
        _head(cv, x, _staff_y(nt), n - f, demo.MUTED)
    cx = xs[-1]
    for nt in LAND:
        _head(cv, cx, _staff_y(nt), n - HIT, demo.ACCENT, r=13)
    if n >= HIT:
        age = n - HIT
        cv.line(cx + 12, _staff_y(LAND[0]), cx + 12, _staff_y(LAND[-1]) - 60, demo.ACCENT, width=3)
        ring = vb.clamp01(age / 14)
        if ring < 1:
            cv.arc(cx, _staff_y(LAND[len(LAND) // 2]), 16 + 80 * (1 - (1 - ring) ** 3), 0, 2 * math.pi, demo.ACCENT,
                   width=4 * (1 - ring), alpha=1 - ring)
        # cairo refuses a zero scale, which the first frame of the pop would give
        s = max(vb.ease_out_back(vb.clamp01(age / 9)), 1e-3)
        wx, wy = demo.W / 2, demo.H / 2 + 100
        with cv.layer(dx=wx * (1 - s), dy=wy * (1 - s), scale=s):
            box = demo.word(cv, 'TA-DA!', wx, wy, size=88, color=demo.INK)
        cv.mark('word', *box)


def demo_film():
    return demo.film(draw, sounds=sting(HIT, TUNE, LAND, gap=GAP, chord_gain_db=-6, hit='pro_impact/short'))


CAPABILITY = Capability(
    id='stinger',
    name='Musical sting',
    family='sound',
    group='Music',
    aliases=('sting', 'musical stinger', 'music sting', 'stinger'),
    definition='A tiny burst of music, often a couple of quick notes landing on one chord, '
               'timed to hit exactly as something is revealed or a joke lands.',
    phrasings=('play a little ta-da when the title appears',
               'a short musical hit to punctuate the punchline',
               'a few notes and a chord right on the reveal'),
    related=('logo-sting', 'foley', 'impact-hit', 'broadcast-title-card-stinger', 'chat-bubble-sequence',
             'kinetic-lyric-typography'),
    api=('videobuilder.capabilities.sound.stinger.sting',
         'videobuilder.capabilities.sound.stinger.sting_frames',
         'videobuilder.sfx.sound'),
    demo=demo_film,
)
