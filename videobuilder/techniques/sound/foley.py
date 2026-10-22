"""Foley: ordinary action sounds -- footsteps, a cup set down, a sleeve
brushing past -- laid in afterwards, each on the frame its movement makes
contact, so the picture sounds real."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

# An action -> the bank sounds that can play it, best first, each with its
# level. Mostly the bank's fitted sounds, made from real recordings, so a cue
# sheet keeps to one family; a plain click is the last resort in every row,
# for a pack that lacks the rest.
LAST_RESORT = ('fit/click/floss_lid', -8.0)
FOLEY_KIT = {
    'step': (('fit/land.light/fingertip_book', -4.0), ('tap/soft', -6.0), LAST_RESORT),
    'set-down': (('fit/land.light/finger_wood', -3.0), ('tap/table', -4.0), LAST_RESORT),
    'tap': (('fit/land.light/finger_phone', -6.0), ('tap/finger', -6.0), LAST_RESORT),
    'knock': (('tap/knuckle', -6.0), ('pro_tap/knock', -6.0), LAST_RESORT),
    'rustle': (('swipe/cloth', -10.0), ('swipe/velvet', -10.0), LAST_RESORT),
}


def _pick(action, choices):
    """The first of `choices` the installed pack has, as (sound id, level)."""
    for sound, level in choices:
        try:
            vb.sfx.get(sound)
        except ValueError:
            continue
        return sound, level
    raise ValueError(f'foley: the pack has none of the sounds for {action!r}: '
                     f'{", ".join(c[0] for c in choices)}')


def foley(cues, gain_db=0.0, kit=None):
    """Sound effects for a cue sheet of on-screen actions: each cue is
    `(frame, action)` or `(frame, action, gain_db)`, with `action` a key of
    `kit` (default `FOLEY_KIT`: step, set-down, tap, knock, rustle) and its
    sound's peak on `frame`, the frame of contact. A kit row lists
    `(sound id, gain_db)` choices, best first; the first the pack has plays.
    `gain_db` lifts or lowers the whole sheet. Returns a tuple for a
    `Film`'s `sounds=`."""
    kit = FOLEY_KIT if kit is None else kit
    out = []
    for cue in cues:
        frame, action, extra = (*cue, 0.0) if len(cue) == 2 else cue
        if action not in kit:
            raise KeyError(f'foley: no sound for action {action!r}; the kit has {", ".join(kit)}')
        sound, level = _pick(action, kit[action])
        dur = 0.5 if sound.startswith('swipe/') else None
        out.append(vb.sfx.sound(sound, at=frame, gain_db=level + gain_db + extra, dur=dur))
    return tuple(out)


def footfalls(first, every, count):
    """The contact frames of `count` steps, the first on frame `first` and
    one each `every` frames after: the frames a walk's step sounds go on."""
    return tuple(round(first + i * every) for i in range(count))


# ---- the demo: a pair of shoes walks across, then a cup is set down ----
FLOOR = 330
STEPS = footfalls(18, 9, 6)                 # plants at 0.6 s .. 2.1 s
CUP_DOWN = 75                               # 2.5 s
CUES = tuple((f, 'step') for f in STEPS) + ((CUP_DOWN, 'set-down'),)
STRIDE = 70
LANE_Y, LANE_X0, LANE_X1 = 470, 120, demo.W - 120


def _shoe(cv, x, lift, color):
    """A shoe in profile, its heel at `x`, `lift` px off the floor."""
    y = FLOOR - lift
    tilt = min(lift, 18) * 0.35
    cv.rect(x, y - 30 - tilt, 70, 30 + tilt, color, radius=10)     # the upper
    cv.rect(x + 40, y - 18, 56, 18, color, radius=9)               # the toe
    cv.rect(x - 2, y - 6, 100, 7, demo.INK, radius=3, alpha=0.85)  # the sole


def _foot(n, k):
    """Heel x and lift of foot `k` (0 back, 1 front) at frame `n`: each foot
    swings forward in the frames before each of its own plants."""
    x0 = 130 + k * STRIDE
    x, lift = x0, 0.0
    for i, plant in enumerate(STEPS):
        if i % 2 != k:
            continue
        p = vb.clamp01((n - (plant - 9)) / 9)
        x += 2 * STRIDE * vb.ease_in_out_quart(p)
        if 0 < p < 1:
            lift = 46 * math.sin(math.pi * p)
    return x, lift


def _contact(cv, x, y, age, r=14):
    """Short strokes fanning up from a contact point, fading over 8 frames."""
    if not 0 <= age < 8:
        return
    q = age / 8
    for a in (-2.4, -1.9, -1.25, -0.7):
        r0, r1 = r + 26 * q, r + 12 + 34 * q
        cv.line(x + r0 * math.cos(a), y + r0 * math.sin(a), x + r1 * math.cos(a), y + r1 * math.sin(a),
                demo.ACCENT, width=3, alpha=1 - q)


def _cup(cv, n):
    """A mug lowered onto the floor, landing on `CUP_DOWN`."""
    p = vb.clamp01((n - (CUP_DOWN - 18)) / 18)
    if n < CUP_DOWN - 24:
        return
    x, y = 780, FLOOR - 150 * (1 - vb.ease_out_quint(p))
    alpha = vb.clamp01((n - (CUP_DOWN - 24)) / 6)
    _contact(cv, x + 33, FLOOR, n - CUP_DOWN, r=46)   # under the mug, so only its sides show
    cv.outline(x + 52, y - 56, 30, 34, demo.TEAL, width=7, radius=14, alpha=alpha)   # the handle
    cv.rect(x, y - 72, 66, 72, demo.TEAL, radius=8, alpha=alpha)
    cv.rect(x + 8, y - 64, 50, 6, demo.INK, radius=3, alpha=0.35 * alpha)


def _lane(cv, n):
    """The cue sheet under the picture: a mark for every cue, lit with a
    burst of sound once the playhead reaches it."""
    span = LANE_X1 - LANE_X0
    at = lambda f: LANE_X0 + span * f / (demo.FPS * demo.SECONDS)  # noqa: E731
    cv.line(LANE_X0, LANE_Y, LANE_X1, LANE_Y, demo.LINE, width=2)
    demo.word(cv, 'foley', LANE_X0 - 56, LANE_Y, size=18, color=demo.MUTED, weight=700)
    for f, action in CUES:
        x, age = at(f), n - f
        if age < 0:
            cv.rect(x - 2, LANE_Y - 10, 4, 20, demo.MUTED, radius=2, alpha=0.6)
            continue
        decay = math.exp(-age / 6)
        for j in range(-4, 5):                    # a small waveform blip, loudest at contact
            h = 6 + 40 * decay * math.exp(-abs(j) / 1.6) * (0.7 + 0.3 * math.cos(j * 2.1))
            cv.rect(x + j * 6 - 2, LANE_Y - h / 2, 4, h, demo.ACCENT if action == 'step' else demo.TEAL,
                    radius=2, alpha=0.5 + 0.5 * decay)
        demo.word(cv, action, x, LANE_Y + 34, size=16, color=demo.INK, weight=600, alpha=0.4 + 0.6 * decay)
    cv.line(at(n), LANE_Y - 30, at(n), LANE_Y + 22, demo.INK, width=2, alpha=0.8)


def draw(n, cv):
    demo.floor(cv, FLOOR)
    for k, color in ((0, demo.MUTED), (1, demo.ACCENT)):
        x, lift = _foot(n, k)
        _shoe(cv, x, lift, color)
        cv.mark(f'shoe{k}', x, FLOOR - 50, 100, 50)
    for i, plant in enumerate(STEPS):
        x, _ = _foot(plant, i % 2)
        _contact(cv, x + 48, FLOOR, n - plant)
    _cup(cv, n)
    _lane(cv, n)


TECHNIQUE = Technique(
    id='foley',
    name='Foley',
    family='sound',
    group='Sound effects',
    aliases=('foley sounds', 'foley art', 'foley effects'),
    definition='Everyday sounds of the action on screen, such as footsteps or a cup touching a table, '
               'are added afterwards and lined up with the exact frames where things make contact.',
    phrasings=('add footstep sounds that hit right as each foot lands',
               'give the movements real-world sounds, like steps and things being put down',
               'sync little action noises to what happens on screen'),
    related=('stop-motion-animation', 'sound-bridge', 'rotoscope-look', 'analog-ghosting', 'ambience',
             'staging'),
    api=('videobuilder.techniques.sound.foley.foley', 'videobuilder.techniques.sound.foley.footfalls',
         'videobuilder.sfx.sound'),
    demo=lambda: demo.film(draw, sounds=foley(CUES)),
)
