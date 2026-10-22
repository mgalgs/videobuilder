"""2D Character Rig: a flat character cut into parts, each hung on a joint in
its parent, so turning one joint carries everything below it along.

videobuilder's `vb.Stick` is a ready-made rig in line art; this is the
general one for flat shapes. A rig is a tuple of `Part`s, parents before
children; a pose is a dict of joint angles; `solve` runs the chain and
`draw_rig` paints it.

    RIG = (part('torso', None, (0, 0), (-40, -120, 80, 120), '#7f86ff', radius=20),
           limb('arm', 'torso', (30, -110), 70, 18, '#f2b400'),
           limb('hand', 'arm', (0, 70), 60, 16, '#f2b400'))
    draw_rig(cv, RIG, {'arm': -60, 'hand': -30}, x, ground_y)
"""
import math
from dataclasses import dataclass

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


@dataclass(frozen=True)
class Part:
    """One rigid piece of a rig. `parent` names the part it hangs from (None
    for the root); `at` is its joint, in the parent's own frame (the root's
    is the rig's origin). `box` (x, y, w, h) is the shape, in this part's
    frame with the joint at (0, 0) and +y running down the part at rest.
    `rest` is its angle in degrees before any pose (clockwise on screen).
    Lower `z` draws first. `draw(cv)`, if given, paints extra detail (a
    face) in the part's frame, after its box."""
    name: str
    parent: object
    at: tuple
    box: tuple
    color: object
    radius: float = 0.0
    rest: float = 0.0
    z: int = 0
    draw: object = None


def part(name, parent, at, box, color, **kw):
    """A `Part`; `kw` is `radius`, `rest`, `z` or `draw`."""
    return Part(name, parent, tuple(at), tuple(box), color, **kw)


def limb(name, parent, at, length, width, color, **kw):
    """A rounded bar from its joint down `length` px: its tip, where a child
    limb hangs, is at (0, `length`) in its frame."""
    return Part(name, parent, tuple(at), (-width / 2, -width / 2, width, length + width), color,
                radius=width / 2, **kw)


def _turn(px, py, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return px * c - py * s, px * s + py * c


def solve(parts, pose, x, y, scale=1.0, angle=0.0):
    """Forward kinematics: every part's joint on screen and its world angle,
    as `{name: (jx, jy, deg)}`. The root's joint sits at (x, y), turned by
    `angle`; each part's angle is its parent's plus its `rest` plus
    `pose.get(name, 0)`, so a turn at a joint carries every child with it."""
    out = {}
    for p in parts:
        if p.parent is None:
            jx, jy, base = x + p.at[0] * scale, y + p.at[1] * scale, angle
        else:
            if p.parent not in out:
                raise ValueError(f'part {p.name!r} comes before its parent {p.parent!r}')
            px, py, base = out[p.parent]
            dx, dy = _turn(p.at[0] * scale, p.at[1] * scale, base)
            jx, jy = px + dx, py + dy
        out[p.name] = (jx, jy, base + p.rest + pose.get(p.name, 0.0))
    return out


def draw_rig(cv, parts, pose, x, y, scale=1.0, angle=0.0, joints=False, joint_color='#ffffff', mark=None):
    """Draw `parts` posed by `pose` (joint angles in degrees, clockwise) with
    the root's joint at (x, y). `joints` dots each child's pivot, to show
    the rig (a part with an empty box only carries its `draw`). Returns the solved joints (see `solve`) and marks the
    character's bounding box as `mark` when given."""
    solved = solve(parts, pose, x, y, scale, angle)
    c = cv.ctx
    xs, ys = [], []
    for p in sorted(parts, key=lambda p: p.z):
        jx, jy, deg = solved[p.name]
        bx, by, bw, bh = p.box
        for cx, cy in ((bx, by), (bx + bw, by), (bx, by + bh), (bx + bw, by + bh)):
            dx, dy = _turn(cx * scale, cy * scale, deg)
            xs.append(jx + dx)
            ys.append(jy + dy)
        c.save()
        c.translate(jx, jy)
        c.rotate(math.radians(deg))
        c.scale(scale, scale)
        cv.rect(bx, by, bw, bh, p.color, radius=p.radius)
        if p.draw:
            p.draw(cv)
        c.restore()
    if joints:
        r = 5 * scale
        for p in parts:
            if p.parent is not None and p.box[2] and p.box[3]:   # end pieces (a hand) have no joint below
                jx, jy, _ = solved[p.name]
                demo.dot(cv, jx, jy, r, joint_color)
                demo.dot(cv, jx, jy, r * 0.45, demo.BG)
    if mark and xs:
        cv.mark(mark, min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
    return solved


# ---- the demo figure: hips at the origin, about 300 px tall ----
BODY, SKIN, HANDS = '#7f86ff', '#f2b400', demo.INK


def _face(cv):
    cv.rect(-12, -40, 7, 9, demo.BG, radius=3)
    cv.rect(5, -40, 7, 9, demo.BG, radius=3)
    cv.arc(0, -30, 13, math.radians(30), math.radians(150), demo.BG, width=3)


def _hand(cv):
    demo.dot(cv, 0, 0, 11, HANDS)


def _foot(cv):
    cv.rect(-6, -6, 30, 12, HANDS, radius=6)


FIGURE = (
    part('torso', None, (0, 0), (-34, -120, 68, 132), BODY, radius=22, z=1),
    part('head', 'torso', (0, -126), (-30, -62, 60, 62), SKIN, radius=18, z=2, draw=_face),
    limb('back_thigh', 'torso', (-17, 0), 60, 22, BODY, z=0),
    limb('back_shin', 'back_thigh', (0, 60), 58, 20, BODY, z=0),
    part('back_foot', 'back_shin', (0, 58), (0, 0, 0, 0), HANDS, z=0, draw=_foot),
    limb('front_thigh', 'torso', (17, 0), 60, 22, BODY, z=0),
    limb('front_shin', 'front_thigh', (0, 60), 58, 20, BODY, z=0),
    part('front_foot', 'front_shin', (0, 58), (0, 0, 0, 0), HANDS, z=0, draw=_foot),
    limb('left_arm', 'torso', (-32, -108), 62, 16, SKIN, rest=8, z=3),
    limb('left_forearm', 'left_arm', (0, 62), 56, 14, SKIN, z=3),
    part('left_hand', 'left_forearm', (0, 58), (0, 0, 0, 0), HANDS, z=3, draw=_hand),
    limb('right_arm', 'torso', (32, -108), 62, 16, SKIN, rest=-8, z=3),
    limb('right_forearm', 'right_arm', (0, 62), 56, 14, SKIN, z=3),
    part('right_hand', 'right_forearm', (0, 58), (0, 0, 0, 0), HANDS, z=3, draw=_hand),
)
LEGS = 118  # hip to the soles
SCALE = 1.3


def draw(n, cv):
    ground = demo.H / 2 + 200
    demo.floor(cv, ground, demo.LINE)
    up = vb.ease_in_out_quart(demo.phase(n, 0.3, 1.0))         # the shoulder lifts the whole arm
    wave = math.sin(2 * math.pi * max(0.0, n / demo.FPS - 1.0) / 0.7) * demo.phase(n, 0.9, 1.2)
    lean = up * 6
    pose = {
        'torso': lean,
        'head': -lean * 1.6 + 5 * up,
        'right_arm': -115 * up,                               # forearm and hand come along
        'right_forearm': -45 * up + 42 * wave,                # then the elbow waves on its own
        'right_hand': 0,
        'left_arm': -6 * up,
        'left_forearm': -14 * up,
        'back_thigh': -lean, 'front_thigh': -lean,
    }
    draw_rig(cv, FIGURE, pose, demo.W / 2, ground - (LEGS + 6) * SCALE, scale=SCALE, joints=True, mark='character')


TECHNIQUE = Technique(
    id='flat-character-rig',
    name='2D character rig',
    family='shapes',
    group='Characters & rigs',
    aliases=('flat character rig', 'puppet rig', 'skeletal 2D rig', 'bone-based vector rig'),
    definition='A flat cut-out character built from separate pieces pinned at joints, so turning a '
               'shoulder swings the forearm and hand with it as the figure is posed.',
    phrasings=('a simple flat character whose arm swings up from the shoulder and waves',
               'animate a vector person by rotating its limbs at the joints',
               'a jointed paper-doll figure that moves like a puppet'),
    related=('character-rotate-in', 'character-3d-flip', 'variable-font-weight-animation', 'slant-axis-swing',
             'shape-morph-loader', 'text-to-shape-morph'),
    api=('videobuilder.techniques.shapes.flat_character_rig.draw_rig',
         'videobuilder.techniques.shapes.flat_character_rig.solve',
         'videobuilder.techniques.shapes.flat_character_rig.limb',
         'videobuilder.techniques.shapes.flat_character_rig.part',
         'videobuilder.Stick'),
    demo=lambda: demo.film(draw),
)
