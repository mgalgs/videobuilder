"""Success chime: two bright tuned dings a few frames apart, the second
higher, put on the frame where something finishes. The demo lands it on a
circle-check badge, with a ripple leaving the badge on each note."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ..ui.circle_check_draw import draw_circle_check

DING = 'pro_notify/ding_2045'
NOTES = ('G5', 'D6')     # a rising fifth: bright, settled, unmistakably "done"
GAP = 4                  # frames between notes (~0.13 s at 30 fps)


def note_frames(at, notes=NOTES, gap=GAP):
    """The film frame each note of a chime starting at `at` lands on."""
    return tuple(at + i * gap for i in range(len(notes)))


def success_chime(at, notes=NOTES, gap=GAP, effect=DING, gain_db=-10.0, fps=30):
    """A success chime as `vb.sfx` sounds for `Film(sounds=...)`: the tuned
    `effect` played once per note in `notes` (low to high reads as success),
    the first peaking on film frame `at` and each next one `gap` frames later.
    Every note after the first is 1 dB quieter, so the run rings out rather
    than piling up. Returns a tuple of `Sfx`."""
    return tuple(vb.sfx.sound(effect, at=f, note=note, gain_db=gain_db - i, fps=fps)
                 for i, (note, f) in enumerate(zip(notes, note_frames(at, notes, gap))))


START, END = 0.3, 1.5                      # the badge draws over these seconds
LANDS = round((START + 0.86 * (END - START)) * demo.FPS)   # the check's tip lands, the badge pops


def demo_notes():
    """`NOTES` when the installed bank's ding has them, else its two lowest
    (a trimmed bank, such as the tests' own, may carry only a few)."""
    have = vb.sfx.get(DING).notes
    return NOTES if set(NOTES) <= set(have) else have[:2]


def ripple(cv, cx, cy, r, n, frame, color):
    """One ring leaving the badge from `frame`: grows and fades over ~0.7 s."""
    t = (n - frame) / (0.7 * demo.FPS)
    if 0 <= t <= 1:
        rr = r + 170 * vb.ease_out_quint(t)
        pts = [(cx + rr * math.cos(k * math.pi / 48), cy + rr * math.sin(k * math.pi / 48)) for k in range(97)]
        vb.paths.draw(cv, pts, color, width=6 * (1 - t) + 1, alpha=0.8 * (1 - t))


def draw(n, cv):
    cx, cy, r = demo.W / 2, demo.H / 2 - 40, 140
    for f in note_frames(LANDS):
        ripple(cv, cx, cy, r, n, f, demo.TEAL)
    box = draw_circle_check(cv, cx, cy, r, demo.phase(n, START, END), demo.TEAL, fill=demo.TEAL)
    cv.mark('badge', *box)
    for i, (note, f) in enumerate(zip(NOTES, note_frames(LANDS))):   # the two notes, stepping up
        a = vb.clamp01((n - f) / 4)
        if a > 0:
            lift = 24 * vb.ease_out_back(a)
            demo.dot(cv, cx + r + 70 + 70 * i, cy - 40 - 60 * i - lift, 16, color=demo.ACCENT, alpha=a)
    a = demo.phase(n, 1.8, 2.3)
    if a > 0:
        demo.word(cv, 'Payment sent', cx, cy + r + 90, size=56, alpha=a)


TECHNIQUE = Technique(
    id='success-chime',
    name='Success chime',
    family='sound',
    group='Sound effects',
    aliases=('confirmation sound', 'completion sound', 'ding'),
    definition='A quick, bright pair of rising tones that plays on the moment an action completes, '
               'telling the viewer it worked.',
    phrasings=('play a happy little ding when the checkmark appears',
               'add a two-note confirmation sound when the payment goes through',
               'a rising chime on the success moment'),
    related=('circle-check-draw', 'button-ending', 'bouncing-ball-word-marker', 'karaoke-highlight-sweep',
             'like-heart-burst', 'sine-wave-text'),
    api=('videobuilder.techniques.sound.success_chime.success_chime',
         'videobuilder.sfx.sound'),
    demo=lambda: demo.film(draw, sounds=success_chime(LANDS, notes=demo_notes())),
)
