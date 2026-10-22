"""Mickey-mousing: the score copies the action beat for beat, one note on
every step, hop or fall, so the music sounds like the movement looks. A
film lists the frames its subject lands on and gets a tuned sound on each,
walking a scale down as it descends (or up as it climbs)."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

MAJOR = (0, 2, 4, 5, 7, 9, 11)
_NAMES = ('C', 'Cs', 'D', 'Ds', 'E', 'F', 'Fs', 'G', 'Gs', 'A', 'As', 'B')


def _midi(note):
    name = vb.sfx.note_name(note)
    letter = name[:2] if name[1:2] == 's' else name[:1]
    return 12 * (int(name[len(letter):]) + 1) + _NAMES.index(letter)


def _name(midi):
    return f'{_NAMES[midi % 12]}{midi // 12 - 1}'


def scale_run(start='C5', count=8, step=-1, scale=MAJOR):
    """`count` note names walking `scale` from `start` (which should be on
    the scale, counted from its octave's C), `step` degrees at a time: -1 runs
    down a step per note, 1 up, 2 in thirds."""
    root = _midi(start)
    base, pc = root - root % 12, root % 12
    degree = min(range(len(scale)), key=lambda i: abs(scale[i] - pc))
    out = []
    for i in range(count):
        octave, d = divmod(degree + i * step, len(scale))
        out.append(_name(base + 12 * octave + scale[d]))
    return out


def mickey_mouse(frames, notes=None, sound='pluck/kalimba', gain_db=-8.0, fps=30, align='onset'):
    """One `vb.sfx` placement per action: `frames` are the film frames the
    subject lands (or steps, or hits) on, and each gets `sound` with its
    `align` point on that frame, playing the matching note of `notes` (cycled
    if shorter; see `scale_run`). A note the sound lacks is played as its
    nearest one; an untuned sound ignores `notes`. Put the result in the
    film's `sounds`."""
    effect = vb.sfx.get(sound)
    have = {_midi(n): n for n in effect.notes}
    out = []
    for i, at in enumerate(frames):
        note = None
        if notes and have:
            want = _midi(notes[i % len(notes)])
            note = have[min(have, key=lambda m: (abs(m - want), m))]
        out.append(effect.sound(at, fps=fps, align=align, gain_db=gain_db, note=note))
    return tuple(out)


# ---- the demo: a ball hops down a staircase, one falling note per step ----
STEPS = 7                       # stair treads below the top landing; the last hop lands on the floor
HOP = 0.3                       # seconds per hop
START = 0.3                     # first take-off
CONTACT = 0.08                  # seconds the ball sits squashed after each landing
LIFT = 48                       # hop height above the straight line between treads
NOTES = scale_run('C5', STEPS + 1)
LANDS = [round((START + (i + 1) * HOP) * demo.FPS) for i in range(STEPS + 1)]
R = 16
X0, X1 = 150, 820               # left edge of the top tread, right end of the floor run
TOP, FLOOR = 250, 470           # top tread's surface, the floor
TREAD = (X1 - X0) / (STEPS + 2)
RISE = (FLOOR - TOP) / (STEPS + 1)
STAFF_Y, STAFF_GAP = 60, 13     # top line of the five-line staff, line spacing


def _surface(i):
    """(centre x, surface y) of landing `i`: 0 is the top, STEPS + 1 the floor."""
    return X0 + TREAD * (i + 0.5), TOP + RISE * i


def _voice():
    """The tuned sound to play: the kalimba pluck, or a ding where the pack lacks it."""
    for sid in ('pluck/kalimba', 'pro_notify/ding_2045'):
        try:
            if vb.sfx.get(sid).tuned:
                return sid
        except ValueError:
            continue
    return None


def _ball(t):
    """(x, y, squash) of the ball at `t` seconds: hops between landings with
    a short squash on each touch-down."""
    k = (t - START) / HOP
    if k <= 0:
        x, y = _surface(0)
        return x, y - R, 0.0
    if k >= STEPS + 1:
        x, y = _surface(STEPS + 1)
        since = (t - (START + (STEPS + 1) * HOP))
        return x, y - R, max(0.0, 1 - since / CONTACT)
    i, u = int(k), k - int(k)
    hold = CONTACT / HOP if i > 0 else 0.0  # sits squashed on the tread it just struck, then springs off
    if u < hold:
        x, y = _surface(i)
        return x, y - R, 1 - u / hold
    u = (u - hold) / (1 - hold)
    (xa, ya), (xb, yb) = _surface(i), _surface(i + 1)
    x = xa + (xb - xa) * u
    y = ya + (yb - ya) * u - 4 * LIFT * u * (1 - u) - R
    return x, y, 0.0


def _note_head(cv, x, y, color, alpha, scale=1.0):
    w, h = 9 * scale, 6.5 * scale
    cv.ctx.save()
    cv.ctx.translate(x, y)
    cv.ctx.rotate(-0.35)
    cv.ctx.scale(1, h / w)
    demo.dot(cv, 0, 0, w, color=color, alpha=alpha)
    cv.ctx.restore()
    cv.line(x + w - 1, y, x + w - 1, y - 34 * scale, color, width=2.2 * scale, alpha=alpha)


def draw(n, cv):
    t = n / demo.FPS
    # the stairs
    for i in range(STEPS + 1):
        x, y = _surface(i)
        cv.rect(x - TREAD / 2, y, TREAD + 1, FLOOR - y, '#2a2f3a')
        cv.line(x - TREAD / 2, y, x + TREAD / 2, y, demo.MUTED, width=3)
    demo.floor(cv, FLOOR)
    # the staff: each note appears as it plays, drawing the melody the ball makes
    left, right = 120, 840
    for k in range(5):
        cv.line(left, STAFF_Y + k * STAFF_GAP, right, STAFF_Y + k * STAFF_GAP, demo.LINE, width=1.5)
    c5 = _midi('C5')
    for i, (at, note) in enumerate(zip(LANDS, NOTES)):
        if n < at:
            break
        x = _surface(i + 1)[0]
        steps = sum(1 for m in range(_midi(note), c5) if m % 12 in MAJOR)  # diatonic steps below C5
        y = STAFF_Y + 1.5 * STAFF_GAP + steps * STAFF_GAP / 2  # C5 sits in the third space
        if steps >= 7:  # below the staff: a ledger line
            cv.line(x - 13, y, x + 13, y, demo.LINE, width=1.5)
        age = (n - at) / demo.FPS
        fresh = max(0.0, 1 - age / 0.35)
        _note_head(cv, x, y, demo.ACCENT if fresh > 0 else demo.INK, 0.55 + 0.45 * fresh, 1 + 0.5 * fresh ** 2)
        if fresh > 0:
            lx, ly = _surface(i + 1)
            cv.line(x, y + 10, lx, ly - 2 * R - 4, demo.ACCENT, width=1.5, alpha=0.4 * fresh)
            demo.word(cv, note.replace('s', '#'), lx, ly + 22, size=18, color=demo.ACCENT, weight=700, alpha=fresh)
            ring = 1 - fresh  # a ripple on the tread where the note was struck
            cv.ctx.save()
            cv.ctx.translate(lx, ly)
            cv.ctx.scale(1, 0.3)
            cv.arc(0, 0, R + 50 * ring, 0, 2 * math.pi, demo.ACCENT, width=3, alpha=0.8 * fresh)
            cv.ctx.restore()
    # the ball
    x, y, sq = _ball(t)
    sx, sy = 1 + 0.35 * sq, 1 - 0.3 * sq
    cv.ctx.save()
    cv.ctx.translate(x, y + R)
    cv.ctx.scale(sx, sy)
    demo.dot(cv, 0, -R, R, color=demo.TEAL)
    cv.ctx.restore()
    cv.mark('ball', x - R * sx, y + R - 2 * R * sy, 2 * R * sx, 2 * R * sy)


def _film():
    voice = _voice()
    sounds = mickey_mouse(LANDS, NOTES, sound=voice, gain_db=-6) if voice else \
        mickey_mouse(LANDS, sound='fit/click/floss_lid', gain_db=-6)
    return demo.film(draw, sounds=sounds)


TECHNIQUE = Technique(
    id='mickey-mousing',
    name='Mickey-mousing',
    family='sound',
    group='Sound effects',
    aliases=('mickey mousing', 'hitting every action'),
    definition='Music that mimics the motion on screen, landing a note on every step, hop or tumble '
               'so each movement has its own musical beat.',
    phrasings=('play a note every time the ball hits a stair',
               'make the music follow every bounce like an old cartoon',
               'a plink for each step as it walks down, going lower each time'),
    related=('ducking', 'slow-motion', 'icon-hover-bounce', 'like-heart-burst', 'bounce-ease-in',
             'ping-pong-loop'),
    api=('videobuilder.techniques.sound.mickey_mousing.mickey_mouse',
         'videobuilder.techniques.sound.mickey_mousing.scale_run'),
    demo=_film,
)
