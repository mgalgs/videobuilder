"""Button ending: the music stops dead on one short, accented final hit -- a
"button" -- instead of fading out, so the cue (and the shot) closes with a
full stop. `button_ending` builds that last stab from the sfx bank: a short
tuned chord, a tight hit and a sub under it, all landing on one frame.
"""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def button_ending(at, fps=30, chord=('G5', 'B5', 'D6'), length=0.25, tone='pro_notify/ding_2045',
                  hit='pro_impact/short', sub=None, sub_note='G1', gain_db=0.0):
    """The sounds of a button landing on film frame `at`: each note of
    `chord` on the tuned sound `tone`, cut to `length` seconds so it stops
    rather than rings, and a `hit` under it (`hit=None` leaves it out). For
    more weight pass a sub drop, e.g. `sub='pro_sub_drop/ref'`, tuned by
    `sub_note` and cut as short as the chord. `gain_db` shifts the whole
    stab. Put it on the cue's last downbeat and let nothing play after it:

        FILM = vb.Film(..., sounds=(*phrase, *button_ending(at=END_BEAT)))
    """
    out = [vb.sfx.sound(tone, at, fps, note=n, dur=length, gain_db=gain_db - 9) for n in chord]
    if hit:
        out.append(vb.sfx.sound(hit, at, fps, gain_db=gain_db - 6))
    if sub:
        out.append(vb.sfx.sound(sub, at, fps, align='onset', note=sub_note, dur=length + 0.1,
                                gain_db=gain_db - 10))
    return tuple(out)


# ---- the demo: a staccato phrase on a beat grid, then the button, then silence ----
BEAT = 12                                  # frames per beat (150 bpm at 30 fps)
FIRST = 6
MELODY = ('D6', 'B5', 'G5', 'B5', 'E6', 'D6')
NOTES = tuple(FIRST + i * BEAT for i in range(len(MELODY)))
BUTTON = FIRST + len(MELODY) * BEAT        # the next downbeat after the phrase
SECONDS = 4.0                              # long enough that the gallery poster (70%) lands after the button
LANE_Y, LANE_X0, LANE_X1 = 220, 110, demo.W - 110


def _x(frame):
    return LANE_X0 + 520 * frame / BUTTON     # the phrase across the left, the button, then room for silence


def draw(n, cv):
    after = n - BUTTON
    demo.word(cv, 'button ending', demo.W / 2, 70, size=26, color=demo.MUTED, weight=700)
    cv.line(LANE_X0, LANE_Y, LANE_X1, LANE_Y, demo.LINE, width=2)
    for f in NOTES:                         # one short block per note of the phrase
        lit = n >= f
        pop = 1 + 0.35 * (1 - demo.phase(n, f / demo.FPS, (f + 6) / demo.FPS)) if lit else 1
        h = 46 * pop
        cv.rect(_x(f), LANE_Y - h / 2, 30, h, demo.TEAL if lit else demo.MUTED, radius=6,
                alpha=1.0 if lit else 0.35)
    # the button: one tall block, then flat nothing
    lit = after >= 0
    p = demo.phase(n, BUTTON / demo.FPS, (BUTTON + 5) / demo.FPS)
    h = (120 + 40 * (1 - p)) if lit else 120
    bx = _x(BUTTON)
    cv.rect(bx, LANE_Y - h / 2, 42, h, demo.ACCENT if lit else demo.MUTED, radius=8,
            alpha=1.0 if lit else 0.35)
    cv.rect(bx + 60, LANE_Y - 1, LANE_X1 - bx - 60, 3, demo.MUTED, alpha=0.5)   # the silence after it
    demo.word(cv, 'silence', (bx + 60 + LANE_X1) / 2, LANE_Y - 26, size=20, color=demo.MUTED, weight=600,
              alpha=0.8 if lit else 0.0)
    # the playhead runs to the button and stops there
    head = _x(min(n, BUTTON)) - 6
    cv.line(head, LANE_Y - 90, head, LANE_Y + 90, demo.INK, width=2, alpha=0.8 if not lit else 0.0)
    if lit:
        cv.fill(demo.INK, alpha=0.25 * max(0.0, 1 - after / 4))           # a one-frame-ish flash on the hit
        demo.word(cv, 'END.', demo.W / 2, LANE_Y + 190, size=80 * (1 + 0.25 * (1 - p)), color=demo.ACCENT,
                  weight=900)


def _near(id, notes):
    """`notes`, each moved to the nearest one the bank's `id` has (a small
    pack may carry only a few)."""
    have = vb.sfx.get(id).notes
    midi = vb.sfx._note_midi
    return tuple(min(have, key=lambda h: abs(midi(h) - midi(n))) for n in notes)


def sounds():
    tone = 'pro_notify/ding_2045'
    phrase = tuple(vb.sfx.sound(tone, f, demo.FPS, note=m, dur=0.18, gain_db=-12)
                   for f, m in zip(NOTES, _near(tone, MELODY)))
    return phrase + button_ending(BUTTON, demo.FPS, chord=_near(tone, ('G5', 'B5', 'D6')))


CAPABILITY = Capability(
    id='button-ending',
    name='Button ending',
    family='sound',
    group='Music',
    aliases=('button', 'stinger ending', 'hard out', 'cold ending', 'sting out'),
    definition='The music finishes on one short, punchy final hit exactly on a beat and then cuts to silence '
               'instead of fading away.',
    phrasings=('end the music on a hard hit, no fade',
               'give the track a punchy stop right on the last frame',
               'finish with a final stab and then dead silence'),
    related=('stinger', 'silence-drop', 'impact-hit', 'cut-to-the-beat', 'music-swell'),
    api=('videobuilder.capabilities.sound.button_ending.button_ending', 'videobuilder.sfx.sound'),
    demo=lambda: demo.film(draw, SECONDS, sounds=sounds()),
)
