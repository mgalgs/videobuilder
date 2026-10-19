"""Stick figures: one simple, expressive character drawn entirely in code.

    FIG = vb.Stick(height=320)                                # black ink on a white head and body
    pose = FIG.act(n, [(0, 'stand'), (20, 'point'), (50, 'shrug')])   # blends with overlap, breathes in holds
    face = FIG.face_at(n, [(0, 'neutral'), (24, 'happy')])
    FIG.draw(cv, pose, x, ground_y, face=face, blink=FIG.blink(n), prop='mug', mark='hero')

    step = FIG.gait(n, 'walk')        # Step: pose, x travelled along the ground, lift, phase
    FIG.draw(cv, step.pose, x0 + step.x, ground_y - step.lift)     # walks along...
    parallax.draw(cv, LAYERS, step.x)                               # ...or stays put while the ground scrolls

The rig is a big round head with a face, a short rounded white body (or a
single line, `body='line'`), and two arms and two legs with an elbow and a
knee each, all stroked with round caps. A `Pose` is ten angles in degrees,
so any pose is just numbers and any two blend. Limb angles read the same
everywhere: 0 points straight down, 90 straight ahead (the way the figure
faces), 180 straight up, -90 straight behind. Arms are measured from the
body (they lean with it), legs from the vertical; an elbow or knee is the
bend at that joint. Limb lengths are fixed, so no pose or blend stretches
a limb, and `draw` stands every pose on its lowest foot.

Size is one number, `height` (px, standing); colours are `ink` and `fill`.
The scene kit at the bottom (`ground`, `wall`, `door`, `desk`, `hill_path`,
`cafe`) draws backdrops in the same line style. See
skill/make-a-video/reference/stick.md.
"""
import bisect
import math
import random
import re
from collections import namedtuple
from dataclasses import dataclass, fields, replace

from .canvas import rgba
from .ease import bezier, clamp01, damped, ease_in_out_quart, spring_at
from .layout import Box

# ---- proportions, as shares of the standing height ----
THIGH, SHIN = 0.155, 0.145
TORSO = 0.25             # hip to neck
SHOULDER = 0.88          # the shoulders' share of the way up the body
UPPER_ARM, FOREARM = 0.15, 0.14
NECK = 0.015             # gap between the body and the head
BODY_W = 0.15            # the rounded body's width
FOOT = 0.05              # a foot's length, forward from the ankle
WEIGHT = 0.03            # the default line weight
LEG = THIGH + SHIN


def _head_r(weight):
    """The head's radius, so the standing figure measures exactly 1 from the
    bottom of its feet to the top of its head's outline."""
    return (1 - LEG - TORSO - NECK - 1.1 * weight) / 2


def _dir(deg):
    """The unit vector of a limb angle: 0 down, 90 forward, 180 up (y down)."""
    a = math.radians(deg)
    return math.sin(a), math.cos(a)


def _angle(dx, dy):
    """The limb angle of a vector (x forward, y down)."""
    return math.degrees(math.atan2(dx, dy))


def _ik(tx, ty, a, b, sign):
    """Two-bone reach from (0, 0) to (tx, ty) with bones `a` then `b`: the
    world angles of both bones. `sign` +1 bends the joint forward (a knee),
    -1 back (an elbow). A target out of reach is reached for in its direction."""
    d = min(max(math.hypot(tx, ty), abs(a - b) + 1e-6), (a + b) * (1 - 1e-9))
    phi = _angle(tx, ty)
    alpha = math.degrees(math.acos(max(-1.0, min(1.0, (a * a + d * d - b * b) / (2 * a * d)))))
    first = phi + sign * alpha
    jx, jy = _dir(first)
    k = d / max(math.hypot(tx, ty), 1e-9)
    second = _angle(tx * k - a * jx, ty * k - a * jy)
    return first, second


# ---- poses ----
@dataclass(frozen=True)
class Pose:
    """Ten joint angles in degrees. `lean` tilts the body from upright
    (+ forward); `nod` tilts the head on it (+ down). Arms are measured from
    the body, the elbow the bend from the upper arm (+ forearm swings
    forward/up). Legs are measured from the vertical, the knee the bend
    from the thigh (+ shin swings back, as a knee does). `front_` limbs are
    drawn over the body, `back_` limbs behind it."""
    lean: float = 0.0
    nod: float = 0.0
    front_arm: float = 0.0
    front_elbow: float = 0.0
    back_arm: float = 0.0
    back_elbow: float = 0.0
    front_hip: float = 0.0
    front_knee: float = 0.0
    back_hip: float = 0.0
    back_knee: float = 0.0

    def __add__(self, other):
        return Pose(*(getattr(self, f.name) + getattr(other, f.name) for f in fields(Pose)))


_BODY = ('lean', 'front_hip', 'front_knee', 'back_hip', 'back_knee')
_ARMS = ('front_arm', 'front_elbow', 'back_arm', 'back_elbow')
_HEAD = ('nod',)


def blend(a, b, t):
    """The pose `t` of the way from `a` to `b`, every angle eased alike:
    exactly `a` at 0 and `b` at 1 (and past either end for an overshoot)."""
    if t == 0:
        return a
    if t == 1:
        return b
    return Pose(*(getattr(a, f.name) + (getattr(b, f.name) - getattr(a, f.name)) * t for f in fields(Pose)))


def _blend_groups(a, b, tb, ta, th):
    """A blend whose body, arms and head each take their own share."""
    if (tb, ta, th) == (1, 1, 1):
        return b
    if (tb, ta, th) == (0, 0, 0):
        return a
    out = {}
    for f in fields(Pose):
        t = ta if f.name in _ARMS else th if f.name in _HEAD else tb
        x, y = getattr(a, f.name), getattr(b, f.name)
        out[f.name] = x + (y - x) * t
    return Pose(**out)


def _arm_to(hand, lean, sign=-1):
    """(arm, elbow) angles, relative to a body leaning `lean`, that put the
    hand at `hand` (x, y) from the shoulder, in shares of the height."""
    upper, fore = _ik(hand[0], hand[1], UPPER_ARM, FOREARM, sign)
    return upper - lean, fore - upper


def _legs_to(front, back):
    """The four leg angles that put the ankles at `front` and `back` (x, y)
    from the hip, knees forward."""
    out = {}
    for name, (x, y) in (('front', front), ('back', back)):
        thigh, shin = _ik(x, y, THIGH, SHIN, +1)
        out[f'{name}_hip'], out[f'{name}_knee'] = thigh, thigh - shin
    return out


def _skeleton(pose, r):
    """Joint points of `pose` in shares of the height, hip at (0, 0), x
    forward, y down. `r` is the head's radius."""
    j = {'hip': (0.0, 0.0)}
    bx, by = math.sin(math.radians(pose.lean)), -math.cos(math.radians(pose.lean))   # up the body
    j['neck'] = (bx * TORSO, by * TORSO)
    j['shoulder'] = (bx * TORSO * SHOULDER, by * TORSO * SHOULDER)
    head = pose.lean + 0.35 * pose.nod
    hx, hy = math.sin(math.radians(head)), -math.cos(math.radians(head))
    j['head'] = (j['neck'][0] + hx * (NECK + r), j['neck'][1] + hy * (NECK + r))
    sx, sy = j['shoulder']
    for side in ('front', 'back'):
        upper = pose.lean + getattr(pose, f'{side}_arm')
        fore = upper + getattr(pose, f'{side}_elbow')
        ux, uy = _dir(upper)
        fx, fy = _dir(fore)
        ex, ey = sx + UPPER_ARM * ux, sy + UPPER_ARM * uy
        j[f'{side}_elbow'] = (ex, ey)
        j[f'{side}_hand'] = (ex + FOREARM * fx, ey + FOREARM * fy)
        thigh = getattr(pose, f'{side}_hip')
        shin = thigh - getattr(pose, f'{side}_knee')
        tx, ty = _dir(thigh)
        kx, ky = THIGH * tx, THIGH * ty
        j[f'{side}_knee'] = (kx, ky)
        sx2, sy2 = _dir(shin)
        j[f'{side}_ankle'] = (kx + SHIN * sx2, ky + SHIN * sy2)
        ax, ay = j[f'{side}_ankle']
        j[f'{side}_toe'] = (ax + FOOT, ay)
    return j


def _build_poses():
    """The named still poses, posed by where the hands and feet go, so feet
    meant to stand both stand and a hand meant at the chin is at the chin."""
    w = WEIGHT
    r = _head_r(w)
    stand_y = LEG * math.cos(math.radians(4))
    plant = _legs_to((LEG * math.sin(math.radians(4)), stand_y), (-LEG * math.sin(math.radians(4)), stand_y))
    poses = {
        'stand': Pose(front_arm=8, front_elbow=12, back_arm=-8, back_elbow=12, **plant),
    }
    # point: the front arm straight out, a touch above level, the body leaning in.
    lean = 4
    poses['point'] = Pose(lean=lean, nod=-3, front_arm=96 - lean, front_elbow=0, back_arm=-12, back_elbow=18,
                          **_legs_to((0.07, 0.293), (-0.05, 0.293)))
    poses['wave'] = Pose(lean=-2, nod=-2, front_arm=118, front_elbow=34, back_arm=-6, back_elbow=12,
                         **plant)
    # shrug: elbows in, forearms out and up, palms to the sky, head tipped.
    poses['shrug'] = Pose(lean=-3, nod=-6, front_arm=18, front_elbow=92, back_arm=-18, back_elbow=-92,
                          **_legs_to((0.03, 0.296), (-0.03, 0.296)))
    # think: the front hand at the chin, the back arm folded across under it.
    neck_y = -TORSO
    chin = (0.62 * r, neck_y - NECK - r + 0.86 * r)
    shoulder = (0.0, -TORSO * SHOULDER)
    lean = 2
    poses['think'] = Pose(lean=lean, nod=-8,
                          **dict(zip(('front_arm', 'front_elbow'),
                                     _arm_to((chin[0] + 0.01 - shoulder[0], chin[1] + 0.035 - shoulder[1]), lean))),
                          **dict(zip(('back_arm', 'back_elbow'), _arm_to((0.085, 0.13), lean))),
                          **_legs_to((0.04, 0.296), (-0.03, 0.296)))
    # push: leaning into a wall, arms out level past the head's front, back leg driving.
    lean = 16
    sh = (math.sin(math.radians(lean)) * TORSO * SHOULDER, -math.cos(math.radians(lean)) * TORSO * SHOULDER)
    hand = (0.345 - sh[0], -0.205 - sh[1])
    arm = dict(zip(('front_arm', 'front_elbow'), _arm_to(hand, lean)))
    back = dict(zip(('back_arm', 'back_elbow'), _arm_to((hand[0] - 0.012, hand[1] + 0.035), lean)))
    poses['push'] = Pose(lean=lean, nod=-8, **arm, **back, **_legs_to((0.07, 0.255), (-0.15, 0.255)))
    # sit: on a seat at the height of the shins, feet on the floor, hands on the knees.
    lean = -4
    seat = SHIN + 0.012
    legs = _legs_to((THIGH + 0.005, seat), (THIGH - 0.02, seat))
    sh = (math.sin(math.radians(lean)) * TORSO * SHOULDER, -math.cos(math.radians(lean)) * TORSO * SHOULDER)
    poses['sit'] = Pose(lean=lean, nod=0,
                        **dict(zip(('front_arm', 'front_elbow'), _arm_to((0.12 - sh[0], -0.01 - sh[1]), lean))),
                        **dict(zip(('back_arm', 'back_elbow'), _arm_to((0.10 - sh[0], 0.0 - sh[1]), lean))), **legs)
    lean = 26
    sh = (math.sin(math.radians(lean)) * TORSO * SHOULDER, -math.cos(math.radians(lean)) * TORSO * SHOULDER)
    poses['crouch'] = Pose(lean=lean, nod=-22,
                           **dict(zip(('front_arm', 'front_elbow'), _arm_to((0.17 - sh[0], 0.05 - sh[1]), lean))),
                           **dict(zip(('back_arm', 'back_elbow'), _arm_to((0.12 - sh[0], 0.08 - sh[1]), lean))),
                           **_legs_to((0.09, 0.14), (-0.07, 0.14)))
    # hold: an object held out in front at chest height, forearm level.
    poses['hold'] = Pose(lean=0, nod=2, **dict(zip(('front_arm', 'front_elbow'), _arm_to((0.13, 0.085), 0))),
                         back_arm=-8, back_elbow=14, **plant)
    # read: a sheet held open in front with both hands, head down to it.
    poses['read'] = Pose(lean=3, nod=14, **dict(zip(('front_arm', 'front_elbow'), _arm_to((0.17, 0.07), 3))),
                         **dict(zip(('back_arm', 'back_elbow'), _arm_to((0.035, 0.085), 3))), **plant)
    poses['cheer'] = Pose(lean=-4, nod=-10, front_arm=122, front_elbow=26, back_arm=-122, back_elbow=-26,
                          **_legs_to((0.06, 0.294), (-0.06, 0.294)))
    poses['slump'] = Pose(lean=18, nod=26, front_arm=-14, front_elbow=4, back_arm=-20, back_elbow=4,
                          **_legs_to((0.035, 0.29), (-0.02, 0.29)))
    return poses


POSES = _build_poses()
CYCLES = ('walk', 'run', 'wave')


def names():
    """Every named pose: the still ones, then the cycles (walk, run, wave)."""
    return tuple(POSES) + tuple(c for c in CYCLES if c not in POSES)


def _unknown(kind, name, known):
    return ValueError(f'no {kind} {name!r}; the {kind}s are: {", ".join(known)}')


# ---- faces ----
@dataclass(frozen=True)
class Face:
    """An expression as numbers, so any two blend. Eyes: `eyes` their size,
    `open` how open (0 shut), `happy` closed eyes drawn as smiling arcs
    rather than lines, `gaze_x`/`gaze_y` where they look (-1..1, + ahead and
    down). Brows: `brows` how much they show (0 none), `brow` their slant in
    degrees (+ inner ends up, worried; - down, cross), `brow_y` raised (a
    share of the head's radius), `brow_tilt` one raised over the other.
    Mouth: `curve` (-1 frown .. 1 smile), `mouth_open` (0..1), `mouth_w`
    width (share of the radius), `round` (1 an "o"), `teeth` (1 gritted),
    `mouth_x` pushed to one side."""
    eyes: float = 1.0
    open: float = 1.0
    happy: float = 0.0
    gaze_x: float = 0.0
    gaze_y: float = 0.0
    brows: float = 0.0
    brow: float = 0.0
    brow_y: float = 0.0
    brow_tilt: float = 0.0
    curve: float = 0.2
    mouth_open: float = 0.0
    mouth_w: float = 0.34
    round: float = 0.0
    teeth: float = 0.0
    mouth_x: float = 0.0


FACES = {
    'neutral': Face(),
    'happy': Face(eyes=1.05, brows=1, brow=4, brow_y=0.06, curve=1.0, mouth_open=0.3, mouth_w=0.5),
    'worried': Face(eyes=1.08, brows=1, brow=24, brow_y=0.04, gaze_x=-0.35, curve=-0.55, mouth_w=0.3),
    'determined': Face(eyes=0.92, open=0.85, brows=1, brow=-24, curve=-0.1, mouth_open=0.32, mouth_w=0.42,
                       teeth=1),
    'surprised': Face(eyes=1.4, brows=1, brow=6, brow_y=0.14, curve=0.0, mouth_open=0.75, mouth_w=0.26, round=1),
    'thinking': Face(gaze_x=0.45, gaze_y=-0.75, brows=1, brow=-4, brow_y=0.04, brow_tilt=0.12, curve=-0.15,
                     mouth_w=0.2, mouth_x=0.14),
    'sleepy': Face(open=0.28, brows=0, brow=10, brow_y=-0.02, gaze_y=0.4, curve=0.0, mouth_w=0.2),
    'content': Face(open=0.0, happy=1, curve=0.75, mouth_w=0.36),
    'annoyed': Face(open=0.55, brows=1, brow=-14, gaze_x=0.4, curve=-0.35, mouth_w=0.3, mouth_x=-0.05),
}
MOUTHS = {
    'smile': dict(curve=0.8, mouth_open=0.0, round=0.0, teeth=0.0),
    'flat': dict(curve=0.0, mouth_open=0.0, round=0.0, teeth=0.0),
    'frown': dict(curve=-0.7, mouth_open=0.0, round=0.0, teeth=0.0),
    'open': dict(curve=0.4, mouth_open=0.6, round=0.0, teeth=0.0),
    'o': dict(curve=0.0, mouth_open=0.7, round=1.0, teeth=0.0, mouth_w=0.24),
    'gritted': dict(curve=-0.1, mouth_open=0.34, round=0.0, teeth=1.0, mouth_w=0.42),
}


def expressions():
    return tuple(FACES)


def face(name=None, mouth=None, **kw):
    """A Face: the named expression (a Face passes through), then a named
    `mouth` from MOUTHS (smile, flat, frown, open, o, gritted), then any
    field by keyword: `face('happy', gaze_x=-1)`."""
    if name is None:
        f = FACES['neutral']
    elif isinstance(name, Face):
        f = name
    elif name in FACES:
        f = FACES[name]
    else:
        raise _unknown('expression', name, expressions())
    if mouth is not None:
        if mouth not in MOUTHS:
            raise _unknown('mouth', mouth, tuple(MOUTHS))
        f = replace(f, **MOUTHS[mouth])
    return replace(f, **kw) if kw else f


_as_face = face


def blend_faces(a, b, t):
    if t <= 0:
        return a
    if t >= 1:
        return b
    return Face(*(getattr(a, f.name) + (getattr(b, f.name) - getattr(a, f.name)) * t for f in fields(Face)))


# ---- talking ----
_VOWELS = re.compile(r'[aeiouy]+', re.I)


def syllables(word):
    """A rough syllable count, for mouth flaps: vowel groups, a silent final e dropped."""
    w = re.sub(r'[^a-z]', '', word.lower())
    if not w:
        return 1
    n = len(_VOWELS.findall(w))
    if w.endswith('e') and not w.endswith(('le', 'ee')) and n > 1:
        n -= 1
    return max(1, n)


def _words(timings):
    if hasattr(timings, 'track'):          # a vb.speech Narration
        timings = timings.track
    out = []
    for w in timings:
        if isinstance(w, tuple):
            text, a, z = w
        else:
            text, a, z = w.text, w.start, w.end
        out.append((text, a, z))
    return out


def mouth(timings, t):
    """How open the mouth is (0..1) at `t` seconds, flapping to word
    timings: a vb.captions Track, a vb.speech Narration (its words), or
    (text, start, end) tuples. Shut between words; inside one, it opens
    and shuts once a syllable, the syllables sharing the word's time."""
    for text, a, z in _words(timings):
        if a <= t < z:
            k = syllables(text)
            p = (t - a) / (z - a) * k
            return round(math.sin(math.pi * (p % 1.0)) ** 0.6, 4)
    return 0.0


# ---- props ----
@dataclass(frozen=True)
class Prop:
    """Something held: `kind` (sheet, map, mug, phone, pencil, sign), `text`
    for a sign, and `hand` ('front' or 'back')."""
    kind: str
    text: str = ''
    hand: str = 'front'


PROPS = ('sheet', 'map', 'mug', 'phone', 'pencil', 'sign')
_TWO_HANDED = ('sheet', 'map')


def _both_hands(p, j):
    """Is a sheet or map held open in both hands? When it is in the front
    hand and both hands are out in front at the chest, apart but not far
    (as in 'read')."""
    if p is None or p.kind not in _TWO_HANDED or p.hand != 'front':
        return False
    a, b, (sx, sy) = j['back_hand'], j['front_hand'], j['shoulder']
    return (a[0] > sx + 0.02 and b[0] > sx + 0.02 and 0.08 < math.dist(a, b) < 0.32
            and all(-0.05 < h[1] - sy < 0.12 for h in (a, b)))         # both out in front, at the chest


def prop(kind, text='', hand='front'):
    if kind not in PROPS:
        raise _unknown('prop', kind, PROPS)
    if hand not in ('front', 'back'):
        raise ValueError(f"a prop's hand is 'front' or 'back', not {hand!r}")
    return Prop(kind, text, hand)


_as_prop = prop


# ---- the figure ----
Step = namedtuple('Step', 'pose x lift phase contact')
Step.__doc__ = """One frame of `Stick.gait`: the `pose`; `x`, px travelled
along the ground so far (move the figure by it, or scroll the ground by it
for a walk in place); `lift`, px the figure is off the ground (a run's
flight); `phase`, 0..1 through the cycle of two steps; `contact`, the foot
on the ground ('front', 'back', 'both' or None in flight)."""

Drawn = namedtuple('Drawn', 'joints box prop')
Drawn.__doc__ = """What `Stick.draw` drew: `joints`, every joint's (x, y)
on the canvas; `box`, the figure's Box; `prop`, the held prop's anchor (x,
y) on the canvas, or None."""

GAITS = {
    # duty: share of the cycle each foot is down; reach: how far it lands
    # ahead (share of the leg); clear: how high the swinging foot lifts.
    'walk': dict(period=1.0, duty=0.6, reach=0.3, clear=0.12, stand=0.985, lean=4, arms=26, elbow=16, hop=0.0),
    'run': dict(period=0.62, duty=0.38, reach=0.36, clear=0.42, stand=0.93, lean=14, arms=48, elbow=74, hop=0.035),
}


class Stick:
    """One stick figure. `height` px from the soles to the top of the head,
    standing; `ink` its lines and features, `fill` its head and body;
    `weight` its line weight as a share of the height (default 0.03);
    `body` 'round' (a short white body) or 'line' (a single stroke).
    Keep these the same in every clip of a film: put them in its bible."""

    def __init__(self, height=300, ink='#111111', fill='#ffffff', weight=WEIGHT, body='round', fps=30, seed=0):
        if body not in ('round', 'line'):
            raise ValueError(f"body is 'round' or 'line', not {body!r}")
        self.height = float(height)
        self.ink, self.fill = ink, fill
        self.weight = weight
        self.body = body
        self.fps = fps
        self.seed = seed
        self.r = _head_r(weight)
        self._blinks = None

    # ---- poses ----
    def pose(self, name, n=0):
        """The Pose `name` names (a Pose passes through); a cycle (walk,
        run, wave) at frame `n`. An unknown name raises one ValueError
        listing every name."""
        if isinstance(name, Pose):
            return name
        if name in POSES:
            return POSES[name]
        if name in GAITS:
            return self.gait(n, name).pose
        if name == 'wave':
            w = POSES['wave']
            return replace(w, front_elbow=w.front_elbow + 26 * math.sin(2 * math.pi * n / (0.5 * self.fps)))
        raise _unknown('pose', name, names())

    def alive(self, pose, n, amount=1.0):
        """`pose` breathing at frame `n`: the body and shoulders rise and
        fall, the head drifts, and the weight shifts, knees giving a little,
        so a hold is never frozen. Feet stay where they are."""
        if not amount:
            return pose
        fps = self.fps
        b = math.sin(2 * math.pi * n / (3.4 * fps))                       # a breath
        d = math.sin(2 * math.pi * n / (5.3 * fps) + 1.1)                 # the head's drift
        s = 0.5 - 0.5 * math.cos(2 * math.pi * n / (7.1 * fps))          # the weight's shift, 0..1
        k = 3.0 * s * amount
        return pose + Pose(lean=0.7 * b * amount, nod=1.4 * d * amount,
                           front_arm=1.8 * b * amount, back_arm=-1.8 * b * amount,
                           front_hip=k / 2, front_knee=k, back_hip=k / 2, back_knee=k)

    def move(self, a, b, age, frames=12, anticipate=None):
        """The pose `age` frames into a move from `a` to `b` taking `frames`:
        the body leads (with a small wind-up the other way first when
        `anticipate`, which defaults to on for big moves), the arms trail it
        by a quarter of the move and overshoot a little as they land, and
        the head settles last on a spring. Exactly `a` at age 0 and exactly
        `b` once everything has settled."""
        if age <= 0:
            return a
        lag = max(2.0, frames * 0.25)
        settle = frames + 2 * lag + 1.2 * self.fps
        if age >= settle:
            return b
        if anticipate is None:
            anticipate = sum(abs(getattr(a, f) - getattr(b, f)) for f in _BODY + _ARMS) > 120
        body_ease = _ANTICIPATE if anticipate else ease_in_out_quart
        tb = body_ease(clamp01(age / frames))
        p = (age - lag) / frames
        ta = ease_in_out_quart(clamp01(p)) + 0.1 * math.sin(math.pi * clamp01((p - 0.6) / 0.8))   # lands past, settles
        th = spring_at(age - 2 * lag, self.fps, **damped(0.45, hz=2.2)) if age > 2 * lag else 0.0
        return _blend_groups(a, b, tb, ta, th)

    def act(self, n, keys, alive=True):
        """The pose at frame `n` of a performance: `keys` is a list of
        (frame, pose) or (frame, pose, frames) sorted by frame, each moving
        (`move`) from wherever the figure was into its pose over `frames`
        (default 10) and holding it, breathing (`alive`), until the next.
        A pose is a name, a Pose, or a cycle (walk, run, wave), which keeps
        cycling on the film's frame count while it holds; or a function of
        the frame giving a Pose, for a cycle of your own (`lambda n:
        FIG.gait(n, 'run', period=0.5).pose`), which doesn't breathe."""
        i = 0
        while i + 1 < len(keys) and keys[i + 1][0] <= n:
            i += 1
        start, target = keys[i][0], keys[i][1]
        frames = keys[i][2] if len(keys[i]) > 2 else 10
        cyc = callable(target) or (isinstance(target, str) and target in CYCLES)
        to = target(n) if callable(target) else self.pose(target, n)
        if alive and not cyc:
            to = self.alive(to, n)
        if i == 0:
            return to
        return self.move(self.act(n, keys[:i], alive), to, n - start, frames)

    def face_at(self, n, keys, frames=6):
        """The Face at frame `n` of (frame, expression) keys, each easing
        in over `frames` (or a key's own third item) from the face before."""
        i = 0
        while i + 1 < len(keys) and keys[i + 1][0] <= n:
            i += 1
        to = face(keys[i][1])
        if i == 0:
            return to
        k = keys[i][2] if len(keys[i]) > 2 else frames
        return blend_faces(self.face_at(n, keys[:i], frames), to, ease_in_out_quart(clamp01((n - keys[i][0]) / k)))

    def blink(self, n, every=(2.6, 4.8)):
        """How open the eyes are at frame `n` under blinks: 1, or a blink's
        four frames (half, shut, shut, half) at seeded random intervals of
        `every` seconds. Pass it to `draw`."""
        if self._blinks is None or self._blinks[0] != every:
            rnd = random.Random(self.seed)
            at, starts = round(rnd.uniform(0.6, every[0]) * self.fps), []
            while at < 60 * 60 * self.fps:
                starts.append(at)
                at += round(rnd.uniform(*every) * self.fps)
            self._blinks = (every, starts)
        starts = self._blinks[1]
        i = bisect.bisect_right(starts, n) - 1
        if i < 0:
            return 1.0
        return (0.5, 0.0, 0.0, 0.5, 1.0)[min(4, n - starts[i])]

    def turn(self, n, at, frames=6, start=1, end=-1):
        """`facing` for `draw` through a turn from `start` to `end` (1
        right, -1 left) over `frames` from frame `at`: a quick squash to
        the side view and back out the other way."""
        return start + (end - start) * ease_in_out_quart(clamp01((n - at) / frames))

    # ---- cycles ----
    def gait(self, n, kind='walk', period=None, stride=None, start=0):
        """A Step for frame `n` of a walk or run cycle (two steps), from
        frame `start`. `period` is seconds a cycle (walk 1.0, run 0.62);
        `stride` scales how far each foot reaches. Each foot plants and
        stays put on the ground while the body passes over it at a steady
        speed (`Step.x`); the hips rise and fall with the legs, the arms
        swing against them, a run leaves the ground between steps."""
        if kind not in GAITS:
            raise _unknown('gait', kind, tuple(GAITS))
        g = GAITS[kind]
        T = (period or g['period']) * self.fps
        duty = g['duty']
        s = g['reach'] * LEG * (stride or 1.0)
        f = n - start
        phase = (f / T) % 1.0
        stand = g['stand'] * LEG

        def foot(ph):
            ph %= 1.0
            if ph < duty:                                   # down: sliding back under the hip
                return s - 2 * s * ph / duty, 0.0, True
            u = (ph - duty) / (1 - duty)                     # up: swung forward
            if kind == 'run':
                x = -s + 2 * s * ease_in_out_quart(clamp01((u - 0.12) / 0.88))
                lift = g['clear'] * LEG * math.sin(math.pi * min(1.0, u / 0.85)) ** 1.5
            else:
                x = -s + 2 * s * (0.5 - 0.5 * math.cos(math.pi * u))
                lift = g['clear'] * LEG * math.sin(math.pi * u)
            return x, lift, False

        feet = {'front': foot(phase), 'back': foot(phase + 0.5)}
        down = [k for k, (_, _, d) in feet.items() if d]
        if down:
            h = min(math.sqrt(max(stand ** 2 - feet[k][0] ** 2, 0)) for k in down)
            air = 0.0
        else:
            # In flight: the hips coast on an arc from takeoff to landing.
            h = math.sqrt(stand ** 2 - s ** 2)
            u = ((phase - duty) % 0.5) / (0.5 - duty)
            air = g['hop'] * 4 * u * (1 - u)
        targets = {k: (x, h - lift) for k, (x, lift, _) in feet.items()}
        legs = _legs_to(targets['front'], targets['back'])
        sw = math.cos(2 * math.pi * phase)
        bob = math.sin(4 * math.pi * phase)
        pose = Pose(lean=g['lean'], nod=-2 + 1.5 * bob,
                    front_arm=-g['arms'] * sw, front_elbow=g['elbow'] + 0.3 * g['elbow'] * max(0.0, -sw),
                    back_arm=g['arms'] * sw, back_elbow=g['elbow'] + 0.3 * g['elbow'] * max(0.0, sw), **legs)
        lowest = max(y for _, y in targets.values())
        lift = (h - lowest) * self.height + air * self.height
        speed = 2 * s * self.height / (duty * T)
        contact = 'both' if len(down) == 2 else down[0] if down else None
        return Step(pose, speed * f, lift, phase, contact)

    def speed(self, kind='walk', period=None, stride=None):
        """Px a frame the body travels in `gait`."""
        g = GAITS[kind]
        return 2 * g['reach'] * LEG * (stride or 1.0) * self.height / (g['duty'] * (period or g['period']) * self.fps)

    # ---- geometry ----
    def joints(self, pose, x, y, facing=1, lift=0.0, scale=1.0):
        """Every joint of `pose` on the canvas, standing on the ground at
        (x, y) by its lowest foot (`lift` px above it), facing right (1) or
        left (-1), a fraction between for a turn's squash."""
        pose = self.pose(pose)
        H = self.height * scale
        j = _skeleton(pose, self.r)
        ground = max(j['front_ankle'][1], j['back_ankle'][1]) + 0.6 * self.weight
        fx = facing if abs(facing) >= 0.04 else math.copysign(0.04, facing or 1)
        return {k: (x + fx * px * H, y + (py - ground) * H - lift) for k, (px, py) in j.items()}

    def seat(self):
        """The height of a seat (px above the ground) the 'sit' pose sits on."""
        j = _skeleton(POSES['sit'], self.r)
        ground = max(j['front_ankle'][1], j['back_ankle'][1]) + 0.6 * self.weight
        return (ground - (BODY_W / 2 if self.body == 'round' else self.weight / 2)) * self.height

    def box(self, pose, x, y, facing=1, lift=0.0, scale=1.0):
        """The figure's Box on the canvas: its limbs at their line weight and its head."""
        j = self.joints(pose, x, y, facing, lift, scale)
        H = self.height * scale
        pad = 0.6 * self.weight * H                  # half the widest stroke, a foot's
        hx, hy = j['head']
        ry = (self.r + self.weight / 2) * H
        rx = abs(facing) * ry
        x0 = min(min(p[0] for p in j.values()) - pad, hx - rx)
        x1 = max(max(p[0] for p in j.values()) + pad, hx + rx)
        y0 = min(min(p[1] for p in j.values()) - pad, hy - ry)
        y1 = max(max(p[1] for p in j.values()) + pad, hy + ry)
        return Box(x0, y0, x1 - x0, y1 - y0)

    # ---- drawing ----
    def draw(self, cv, pose, x, y, face=None, facing=1, lift=0.0, scale=1.0, turn=0.35, blink=1.0, talk=0.0,
             prop=None, look=None, halo=None, alpha=1.0, mark=None):
        """Draw `pose` standing on the ground at (x, y) by its lowest foot,
        `lift` px above it. `face`: an expression name or Face. `facing` 1
        right, -1 left (or between, mid-turn). `turn` how far the face is
        turned toward where it faces (0 straight out, 0.35 three-quarter, 1
        profile). `blink` multiplies how open the eyes are (`Stick.blink`);
        `talk` opens the mouth (`mouth(...)`); `look` (x, y) overrides the
        gaze. `prop`: a kind name or `prop(...)`, held in its hand. `halo`:
        a colour drawn round every line, so the figure reads over a busy
        picture. `mark` names a `cv.mark` of the figure's box. Returns a
        Drawn (joints, box, prop anchor)."""
        pose = self.pose(pose)
        f = _as_face(face)
        if look is not None:
            f = replace(f, gaze_x=look[0], gaze_y=look[1])
        if isinstance(prop, str):
            prop = _as_prop(prop)
        H = self.height * scale
        j = _skeleton(pose, self.r)
        ground = max(j['front_ankle'][1], j['back_ankle'][1]) + 0.6 * self.weight
        fx = facing if abs(facing) >= 0.04 else math.copysign(0.04, facing or 1)
        c = cv.ctx
        c.save()
        c.translate(x, y - lift)
        c.scale(fx * H, H)
        c.translate(0, -ground)
        if alpha < 1:
            c.push_group()
        if halo is not None:
            self._figure(c, pose, j, f, turn, blink, talk, prop, fx, halo=halo)
        self._figure(c, pose, j, f, turn, blink, talk, prop, fx)
        if alpha < 1:
            c.pop_group_to_source()
            c.paint_with_alpha(alpha)
        c.restore()
        joints = {k: (x + fx * px * H, y - lift + (py - ground) * H) for k, (px, py) in j.items()}
        box = self.box(pose, x, y, facing, lift, scale)
        if mark:
            cv.mark(mark, *box)
        anchor = joints[f'{prop.hand}_hand'] if prop else None
        return Drawn(joints, box, anchor)

    def _figure(self, c, pose, j, f, turn, blink, talk, prop, fx, halo=None):
        w = self.weight
        ink = halo if halo is not None else self.ink
        fill = halo if halo is not None else self.fill
        grow = 2.2 * w if halo is not None else 0.0
        c.set_line_cap(1)        # round
        c.set_line_join(1)

        def stroke(points, width=w):
            c.move_to(*points[0])
            for p in points[1:]:
                c.line_to(*p)
            c.set_source_rgba(*rgba(ink))
            c.set_line_width(width + grow)
            c.stroke()

        def dot(p, rad):
            c.new_path()
            c.arc(p[0], p[1], rad + grow / 2, 0, 2 * math.pi)
            c.set_source_rgba(*rgba(ink))
            c.fill()

        def arm(side):
            stroke([j['shoulder'], j[f'{side}_elbow'], j[f'{side}_hand']])

        def leg(side):
            stroke([j['hip'], j[f'{side}_knee'], j[f'{side}_ankle']])
            stroke([j[f'{side}_ankle'], j[f'{side}_toe']], 1.2 * w)

        held = prop.hand if prop else None
        two = _both_hands(prop, j)
        arm('back')
        if held == 'back':
            self._prop(c, prop, j, ink, fill, fx, grow, two)
        dot(j['back_hand'], 0.75 * w)
        leg('back')
        leg('front')
        # the body
        if self.body == 'round':
            hx, hy = j['hip']
            nx, ny = j['shoulder'][0] * 1.03, j['shoulder'][1] * 1.03
            c.new_path()
            c.move_to(hx, hy)
            c.line_to(nx, ny)
            c.set_line_width(BODY_W + grow)
            c.set_source_rgba(*rgba(ink))
            c.stroke()
            if halo is None:
                c.move_to(hx, hy)
                c.line_to(nx, ny)
                c.set_line_width(BODY_W - 2 * w)
                c.set_source_rgba(*rgba(fill))
                c.stroke()
        else:
            stroke([j['hip'], j['neck']])
        arm('front')             # over the body, under the head: a raised arm passes behind it, the hand on top
        # the head
        hx, hy = j['head']
        c.new_path()
        c.arc(hx, hy, self.r + grow / 2, 0, 2 * math.pi)
        c.set_source_rgba(*rgba(fill))
        c.fill_preserve()
        c.set_source_rgba(*rgba(ink))
        c.set_line_width(w + grow)
        c.stroke()
        if halo is None:
            c.save()
            c.translate(hx, hy)
            c.rotate(math.radians(0.5 * pose.lean + pose.nod * 0.6))
            _draw_face(c, self.r, f, turn, blink, talk, ink, fill, w)
            c.restore()
        if held == 'front':
            self._prop(c, prop, j, ink, fill, fx, grow, two)
        dot(j['front_hand'], 0.75 * w)
        if two:
            dot(j['back_hand'], 0.75 * w)

    def _prop(self, c, p, j, ink, fill, fx, grow, two=False):
        w = self.weight
        hx, hy = j[f'{p.hand}_hand']
        c.save()
        c.set_line_width(w * 0.8 + grow)

        def shape(fill_first=True):
            c.set_source_rgba(*rgba(fill))
            c.fill_preserve()
            c.set_source_rgba(*rgba(ink))
            c.stroke()

        if p.kind in _TWO_HANDED:
            a, b = j['back_hand'], j['front_hand']
            sw, sh = (0.27, 0.2) if p.kind == 'map' else (0.2, 0.26)
            if two:
                cx, base = (a[0] + b[0]) / 2, min(a[1], b[1]) + 0.02
                sw = max(sw, abs(b[0] - a[0]) + 0.03)
            else:
                cx, base = hx + 0.03, hy + 0.02
            x0, y0 = cx - sw / 2, base - sh
            c.rectangle(x0, y0, sw, sh)
            shape()
            if grow == 0:
                c.set_line_width(w * 0.5)
                if p.kind == 'map':
                    for k in (1, 2):                                # folds
                        c.move_to(x0 + sw * k / 3, y0)
                        c.line_to(x0 + sw * k / 3, y0 + sh)
                    c.stroke()
                    c.set_dash([w * 0.9, w * 0.9])
                    c.move_to(x0 + sw * 0.12, y0 + sh * 0.78)
                    c.curve_to(x0 + sw * 0.4, y0 + sh * 0.95, x0 + sw * 0.5, y0 + sh * 0.2, x0 + sw * 0.8,
                               y0 + sh * 0.35)
                    c.stroke()
                    c.set_dash([])
                    k = sh * 0.09
                    cx2, cy2 = x0 + sw * 0.84, y0 + sh * 0.3
                    for d in (-1, 1):                               # the X
                        c.move_to(cx2 - k, cy2 - d * k)
                        c.line_to(cx2 + k, cy2 + d * k)
                    c.stroke()
                else:
                    for k in range(5):                              # lines of writing
                        ly = y0 + sh * (0.18 + 0.15 * k)
                        c.move_to(x0 + sw * 0.15, ly)
                        c.line_to(x0 + sw * (0.85 if k % 3 != 2 else 0.6), ly)
                    c.stroke()
        elif p.kind == 'mug':
            mw, mh = 0.085, 0.095
            x0, y0 = hx + 0.012, hy - mh * 0.55
            c.new_path()
            c.arc(hx + 0.004, hy - mh * 0.08, mh * 0.22, math.pi * 0.5, math.pi * 1.5)   # the handle, in the hand
            c.set_source_rgba(*rgba(ink))
            c.stroke()
            c.rectangle(x0, y0, mw, mh)
            shape()
            if grow == 0:
                c.set_line_width(w * 0.45)
                for k in (0.3, 0.62):                               # a little steam
                    sx = x0 + mw * k
                    c.move_to(sx, y0 - 0.012)
                    c.curve_to(sx - 0.012, y0 - 0.03, sx + 0.012, y0 - 0.045, sx, y0 - 0.065)
                c.stroke()
        elif p.kind == 'phone':
            pw, ph = 0.045, 0.08
            x0, y0 = hx - pw * 0.3, hy - ph * 0.8
            _round_rect(c, x0, y0, pw, ph, 0.01)
            shape()
            if grow == 0:
                c.set_line_width(w * 0.4)
                _round_rect(c, x0 + pw * 0.18, y0 + ph * 0.14, pw * 0.64, ph * 0.66, 0.004)
                c.stroke()
        elif p.kind == 'pencil':
            fore = _angle(hx - j[f'{p.hand}_elbow'][0], hy - j[f'{p.hand}_elbow'][1])
            ang = fore + 70
            dx, dy = _dir(ang)
            back, tip = 0.035, 0.085
            c.move_to(hx - dx * back, hy - dy * back)
            c.line_to(hx + dx * tip, hy + dy * tip)
            c.set_line_width(w * 1.4 + grow)
            c.set_source_rgba(*rgba(ink))
            c.stroke()
            if grow == 0:
                c.move_to(hx - dx * back, hy - dy * back)
                c.line_to(hx + dx * (tip - 0.02), hy + dy * (tip - 0.02))
                c.set_line_width(w * 0.6)
                c.set_source_rgba(*rgba(fill))
                c.stroke()
        elif p.kind == 'sign':
            pole = 0.2
            c.move_to(hx, hy + 0.03)
            c.line_to(hx, hy - pole)
            c.set_source_rgba(*rgba(ink))
            c.stroke()
            bw, bh = 0.32, 0.14
            x0, y0 = hx - bw / 2, hy - pole - bh
            _round_rect(c, x0, y0, bw, bh, 0.012)
            shape()
            if grow == 0 and p.text:
                c.save()
                c.translate(hx, y0 + bh / 2)
                if fx < 0:
                    c.scale(-1, 1)               # the words read the right way round, whichever way it faces
                c.select_font_face('sans-serif', 0, 1)
                size = 0.07
                c.set_font_size(size)
                ext = c.text_extents(p.text)
                if ext.width > bw * 0.84:
                    size *= bw * 0.84 / ext.width
                    c.set_font_size(size)
                    ext = c.text_extents(p.text)
                c.move_to(-ext.width / 2 - ext.x_bearing, -ext.height / 2 - ext.y_bearing)
                c.set_source_rgba(*rgba(ink))
                c.show_text(p.text)
                c.restore()
        c.restore()


_ANTICIPATE = bezier(0.45, -0.32, 0.3, 1.0)


def _round_rect(c, x, y, w, h, r):
    c.new_path()
    c.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    c.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    c.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    c.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    c.close_path()


def _draw_face(c, r, f, turn, blink, talk, ink, fill, w):
    """The face on a head of radius `r` centred on the origin, turned
    `turn` toward +x."""
    turn = clamp01(turn)
    shift = 0.42 * r * turn
    squeeze = 1 - 0.38 * turn
    gx, gy = 0.1 * r * f.gaze_x, 0.08 * r * f.gaze_y
    eye_y = -0.1 * r + gy
    spread = 0.3 * r * squeeze
    re_ = 0.085 * r * f.eyes
    k = clamp01(f.open * blink)
    c.set_source_rgba(*rgba(ink))
    for side in (-1, 1):
        ex = shift + side * spread + gx
        if k > 0.15:
            c.save()
            c.translate(ex, eye_y + re_ * (1 - k) * 0.5)
            c.scale(1, max(k, 0.15))
            c.arc(0, 0, re_, 0, 2 * math.pi)
            c.restore()
            c.fill()
        else:
            c.set_line_width(w * 0.7)
            if f.happy > 0.5:
                c.arc(ex, eye_y + re_ * 0.6, re_ * 1.1, math.pi * 1.1, math.pi * 1.9)
            else:
                c.move_to(ex - re_ * 1.2, eye_y)
                c.line_to(ex + re_ * 1.2, eye_y)
            c.stroke()
        if f.brows > 0.02:
            by = -0.36 * r - f.brow_y * r - (f.brow_tilt * r if side > 0 else 0)
            half = 0.12 * r * squeeze
            # the inner end is the one toward the face's middle: side -1's right end, side 1's left
            rise = math.tan(math.radians(f.brow)) * half
            inner, outer = ex - side * half, ex + side * half
            c.move_to(outer, by + rise)
            c.line_to(inner, by - rise)
            c.set_line_width(w * 0.75)
            c.set_source_rgba(*rgba(ink, f.brows))
            c.stroke()
            c.set_source_rgba(*rgba(ink))
    # the mouth
    o = max(f.mouth_open, 0.55 * talk)
    q = f.round + (1 - f.round) * 0.3 * talk * (1 - f.teeth)
    mw = f.mouth_w * r * (1 - 0.2 * talk * (1 - f.mouth_open)) * squeeze
    mx, my = shift * 0.95 + (f.mouth_x * r) + gx * 0.3, 0.36 * r
    half = mw / 2
    cv_ = f.curve * 0.55 * mw
    steps = 16
    top, bottom = [], []
    rx, ry = half * 0.6, (0.12 + 0.5 * o) * mw * 0.9
    for i in range(steps + 1):
        s = i / steps
        lx = mx - half + 2 * half * s
        bump = 4 * s * (1 - s)                     # the quadratic's shape, 0 at the corners, 1 in the middle
        ty = my + cv_ * bump * (1 - 0.6 * o) - 0.15 * o * mw * bump
        by = my + cv_ * bump + o * 0.9 * mw * bump
        ex_ = mx - rx * math.cos(math.pi * s)
        top.append((lx + (ex_ - lx) * q, ty + (my - ry * math.sin(math.pi * s) - ty) * q))
        bottom.append((lx + (ex_ - lx) * q, by + (my + ry * math.sin(math.pi * s) - by) * q))
    c.set_source_rgba(*rgba(ink))
    if o < 0.06 and q < 0.5:
        c.move_to(*top[0])
        for p in top[1:]:
            c.line_to(*p)
        c.set_line_width(w * 0.8)
        c.stroke()
        return
    c.move_to(*top[0])
    for p in top[1:]:
        c.line_to(*p)
    for p in reversed(bottom):
        c.line_to(*p)
    c.close_path()
    if f.teeth > 0.5:
        c.set_source_rgba(*rgba(fill))
        c.fill_preserve()
        c.set_source_rgba(*rgba(ink))
        c.set_line_width(w * 0.7)
        c.stroke()
        midy = [(a[1] + b[1]) / 2 for a, b in zip(top, bottom)]
        c.move_to(top[0][0], midy[0])
        for p, yy in zip(top[1:], midy[1:]):
            c.line_to(p[0], yy)
        for k in (5, 8, 11):
            c.move_to(top[k][0], top[k][1])
            c.line_to(bottom[k][0], bottom[k][1])
        c.set_line_width(w * 0.45)
        c.stroke()
    else:
        c.set_line_width(w * 0.8)
        c.fill_preserve()
        c.stroke()


# ---- the scene kit: backdrops in the figure's own line style ----
# Each piece takes the figure it is for: its height is the unit, its ink, fill
# and line weight are the piece's, so the set and the cast always match. Pass
# fill=None to leave a piece open over whatever is behind it (a Look's scene,
# a photo, a vb.Picture). Each returns the Box it drew.

def _kit(fig, ink, fill):
    return (fig.height, fig.weight * fig.height * 0.9, fig.ink if ink is None else ink,
            fig.fill if fill == 'fig' else fill)


def _paint(c, ink, fill, width):
    if fill is not None:
        c.set_source_rgba(*rgba(fill))
        c.fill_preserve()
    c.set_source_rgba(*rgba(ink))
    c.set_line_width(width)
    c.stroke()


def _start(cv, width):
    c = cv.ctx
    c.save()
    c.set_line_cap(1)
    c.set_line_join(1)
    c.set_line_width(width)
    return c


def ground(cv, fig, y, x0=0, x1=None, ink=None, alpha=1.0):
    """A flat ground line at `y` from `x0` to `x1` (default: across the canvas)."""
    H, lw, ink, _ = _kit(fig, ink, None)
    x1 = cv.width if x1 is None else x1
    cv.line(x0, y + lw / 2, x1, y + lw / 2, ink, width=lw, alpha=alpha)
    return Box(x0, y, x1 - x0, lw)


def shadow(cv, fig, x, y, k=1.0, alpha=0.16):
    """A soft oval shadow on the ground under a figure at x; `k` shrinks it (a jump)."""
    c = cv.ctx
    w = 0.22 * fig.height * k
    c.save()
    c.translate(x, y)
    c.scale(w, 0.03 * fig.height * k)
    c.arc(0, 0, 1, 0, 2 * math.pi)
    c.restore()
    c.set_source_rgba(*rgba(fig.ink, alpha * k))
    c.fill()
    return Box(x - w, y - 0.03 * fig.height * k, 2 * w, 0.06 * fig.height * k)


def wall(cv, fig, x, y, height=1.25, width=0.4, ink=None, fill='fig', facing=1):
    """A brick wall standing on the ground at `y`, its face at `x` toward a
    figure coming from the left (`facing` 1) or the right (-1). `height`
    and `width` are shares of the figure's height."""
    H, lw, ink, fill = _kit(fig, ink, fill)
    w, h = width * H, height * H
    x0 = x if facing > 0 else x - w
    c = _start(cv, lw)
    c.rectangle(x0, y - h, w, h)
    _paint(c, ink, fill, lw)
    rows = max(3, round(h / (0.11 * H)))
    rh = h / rows
    c.set_line_width(lw * 0.55)
    c.set_source_rgba(*rgba(ink))
    for i in range(1, rows):
        c.move_to(x0, y - i * rh)
        c.line_to(x0 + w, y - i * rh)
    for i in range(rows):
        off = 0.5 if i % 2 else 0.0
        bw = w / 2.5
        k = off
        while k * bw < w - 1:
            if k * bw > 1:
                c.move_to(x0 + k * bw, y - i * rh)
                c.line_to(x0 + k * bw, y - (i + 1) * rh)
            k += 1
    c.stroke()
    c.restore()
    return Box(x0, y - h, w, h)


def door(cv, fig, x, y, open=0.0, width=0.5, height=1.15, ink=None, fill='fig'):
    """A door in its frame, standing on the ground at `y` from `x`; `open`
    0..1 swings it in (the panel narrows to its edge, showing the dark
    doorway)."""
    H, lw, ink, fill = _kit(fig, ink, fill)
    w, h = width * H, height * H
    c = _start(cv, lw)
    c.rectangle(x, y - h, w, h)
    _paint(c, ink, rgba(ink, 0.85) if open > 0 else fill, lw)
    pw = w * (1 - 0.82 * clamp01(open))
    c.move_to(x, y - h)
    c.line_to(x + pw, y - h + 0.04 * h * clamp01(open))
    c.line_to(x + pw, y - 0.04 * h * clamp01(open))
    c.line_to(x, y)
    c.close_path()
    _paint(c, ink, fill, lw)
    if pw > 0.3 * w:
        c.new_path()
        c.arc(x + pw - 0.12 * w, y - 0.47 * h, 0.035 * H, 0, 2 * math.pi)
        c.set_source_rgba(*rgba(ink))
        c.fill()
    c.restore()
    return Box(x, y - h, w, h)


def desk(cv, fig, x, y, width=0.85, height=0.42, laptop=True, ink=None, fill='fig'):
    """A desk on the ground at `y`, its left edge at `x`, with a drawer and
    (`laptop`) an open laptop on it."""
    H, lw, ink, fill = _kit(fig, ink, fill)
    w, h = width * H, height * H
    top = 0.05 * H
    c = _start(cv, lw)
    c.rectangle(x, y - h, w, top)
    _paint(c, ink, fill, lw)
    for lx in (x + 0.06 * w, x + 0.94 * w):
        c.move_to(lx, y - h + top)
        c.line_to(lx, y)
    c.set_source_rgba(*rgba(ink))
    c.stroke()
    c.rectangle(x + 0.55 * w, y - h + top, 0.32 * w, 0.32 * h)
    _paint(c, ink, fill, lw)
    c.move_to(x + 0.66 * w, y - h + top + 0.16 * h)
    c.line_to(x + 0.76 * w, y - h + top + 0.16 * h)
    c.stroke()
    if laptop:
        lx, ly = x + 0.2 * w, y - h
        c.move_to(lx, ly)
        c.line_to(lx + 0.3 * w, ly)
        c.stroke()
        c.move_to(lx + 0.27 * w, ly)
        c.line_to(lx + 0.33 * w, ly - 0.2 * H)
        c.line_to(lx + 0.13 * w, ly - 0.2 * H)
        c.line_to(lx + 0.07 * w, ly)
        c.close_path()
        _paint(c, ink, fill, lw)
    c.restore()
    return Box(x, y - max(h, h + 0.2 * H if laptop else h), w, h + (0.2 * H if laptop else 0))


def hill_path(cv, fig, x0, x1, y, height=0.7, flag=True, ink=None, fill='fig'):
    """A gentle hill on the ground at `y` from `x0` to `x1`, `height` x the
    figure's height at its crest, with a dashed path winding up it to a
    flag. Returns the hill's Box."""
    H, lw, ink, fill = _kit(fig, ink, fill)
    h = height * H
    w = x1 - x0

    def crest(t):
        return y - h * math.sin(math.pi * t) ** 1.6

    c = _start(cv, lw)
    steps = 48
    c.move_to(x0, y)
    for i in range(steps + 1):
        t = i / steps
        c.line_to(x0 + w * t, crest(t))
    c.line_to(x1, y)
    c.close_path()
    _paint(c, ink, fill, lw)
    c.set_dash([lw * 1.6, lw * 1.8])
    c.set_line_width(lw * 0.6)
    c.move_to(x0 + 0.08 * w, y - 0.04 * h)
    for i in range(1, 25):
        t = i / 24
        px = x0 + w * (0.08 + 0.42 * t + 0.07 * math.sin(3 * math.pi * t) * (1 - t))
        c.line_to(px, crest((px - x0) / w) + 0.12 * h * (1 - t) + 0.02 * h)
    c.stroke()
    c.set_dash([])
    if flag:
        fx, fy = x0 + 0.5 * w, crest(0.5)
        c.set_line_width(lw * 0.8)
        c.move_to(fx, fy)
        c.line_to(fx, fy - 0.28 * H)
        c.stroke()
        c.move_to(fx, fy - 0.28 * H)
        c.line_to(fx + 0.14 * H, fy - 0.235 * H)
        c.line_to(fx, fy - 0.19 * H)
        c.close_path()
        _paint(c, ink, ink, lw * 0.6)
    c.restore()
    return Box(x0, y - h - (0.28 * H if flag else 0), w, h + (0.28 * H if flag else 0))


def cafe(cv, fig, x, y, facing=1, table=True, mug=False, ink=None, fill='fig'):
    """A café chair for a figure sitting at `x` on the ground at `y` (its
    seat at `fig.seat()`, the back behind the figure), and (`table`) a
    small round table in front of it, a mug on it with `mug`. Draw it
    before the figure."""
    H, lw, ink, fill = _kit(fig, ink, fill)
    seat = fig.seat()
    c = _start(cv, lw)
    back = x - facing * 0.13 * H
    front = x + facing * 0.1 * H
    c.move_to(back, y - seat - 0.38 * H)              # the chair's back, bent wire
    c.line_to(back, y)
    c.move_to(back, y - seat)
    c.line_to(front, y - seat)
    c.line_to(front, y)
    c.set_source_rgba(*rgba(ink))
    c.stroke()
    out = Box(min(back, front), y - seat - 0.38 * H, abs(front - back), seat + 0.38 * H)
    if table:
        tx = x + facing * 0.5 * H
        th = 0.4 * H
        tw = 0.16 * H
        c.move_to(tx, y - th)
        c.line_to(tx, y)
        c.move_to(tx - 0.08 * H, y)
        c.line_to(tx + 0.08 * H, y)
        c.stroke()
        c.save()
        c.translate(tx, y - th)
        c.scale(tw, 0.025 * H)
        c.arc(0, 0, 1, 0, 2 * math.pi)
        c.restore()
        _paint(c, ink, fill, lw)
        if mug:
            mw, mh = 0.075 * H, 0.08 * H
            c.rectangle(tx - mw / 2 + 0.03 * H * facing, y - th - mh, mw, mh)
            _paint(c, ink, fill, lw * 0.8)
        out = Box(min(out.x, tx - tw), out.y, max(out.x + out.w, tx + tw) - min(out.x, tx - tw), out.h)
    c.restore()
    return out
