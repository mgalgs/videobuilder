"""Stop-motion animation: the subject only changes pose a dozen or so times a
second and holds in between, and every pose is set down by hand slightly off
-- a nudge, a tilt, a lump in the clay that wasn't there last frame."""
import math
import random
from dataclasses import dataclass

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


@dataclass(frozen=True)
class Pose:
    """One shot of a stop-motion take. `t`: the time the pose was set for
    (seconds, snapped to the shooting rate). `index`: which shot it is, a
    seed for anything else that should change shot to shot (a lumpy outline,
    a fingerprint). `dx`, `dy` (px), `angle` (radians) and `scale` (around 1):
    the hand's small error in setting it down."""
    t: float
    index: int
    dx: float
    dy: float
    angle: float
    scale: float


def stop_motion(t, rate=12, seed=0, nudge=2.0, tilt=1.2, squish=0.015):
    """The stop-motion pose at time `t` seconds: the motion is shot `rate`
    times a second (12: on twos-and-a-half at 30 fps; 10: on threes), so
    animate with `pose.t` instead of `t` and it holds between shots. Each shot
    adds a seeded handling error of up to `nudge` px, `tilt` degrees and
    `squish` of scale, the same every time that shot is drawn. Use one `seed`
    per object so separate puppets aren't nudged in step."""
    index = math.floor(t * rate + 1e-9)
    r = random.Random(f'{seed}:{index}')
    return Pose(t=index / rate, index=index,
                dx=r.uniform(-1, 1) * nudge, dy=r.uniform(-1, 1) * nudge,
                angle=math.radians(r.uniform(-1, 1) * tilt), scale=1 + r.uniform(-1, 1) * squish)


def lumpy(cx, cy, rx, ry, seed, lumps=0.035, points=48):
    """A closed outline of an ellipse (centre, radii) pressed out of clay:
    gently lumpy, the lumps seeded by `seed` (pass the pose's `index` so they
    shift shot to shot). Draw it with `videobuilder.paths.draw(..., fill=True)`."""
    r = random.Random(f'lumpy:{seed}')
    waves = [(k, r.uniform(-1, 1) * lumps / k ** 0.6, r.uniform(0, 2 * math.pi)) for k in range(2, 7)]
    out = []
    for i in range(points):
        a = 2 * math.pi * i / points
        bump = 1 + sum(amp * math.sin(k * a + ph) for k, amp, ph in waves)
        out.append((cx + rx * bump * math.cos(a), cy + ry * bump * math.sin(a)))
    return out


CLAY, CLAY_DARK = '#f2b632', '#c98a12'


def _puppet(cv, x, ground, hop, pose):
    """A clay blob with eyes, its feet `hop` px off the `ground`, at `pose`."""
    land = max(0.0, 1 - hop / 9)  # squashes as it nears the floor
    rx, ry = 46 * (1 + 0.10 * land) * pose.scale, 60 * (1 - 0.10 * land) * pose.scale
    cy = ground - 15 - hop - ry + pose.dy
    x += pose.dx
    c = cv.ctx
    near = 1 - min(1.0, hop / 60)
    c.save()
    c.translate(x, ground + 4)
    c.scale(1, 0.18)
    demo.dot(cv, 0, 0, 40 + 20 * near, color='#000000', alpha=0.12 + 0.25 * near)
    c.restore()
    c.save()
    c.translate(x, cy)
    c.rotate(pose.angle)
    for side in (-1, 1):  # feet, each pressed on its own
        vb.paths.draw(cv, lumpy(side * 20, ry + 9, 15, 6.5, (pose.index, side)), CLAY_DARK, fill=True)
    vb.paths.draw(cv, lumpy(0, 0, rx, ry, pose.index), CLAY, fill=True)
    vb.paths.draw(cv, lumpy(-rx * 0.28, -ry * 0.32, rx * 0.34, ry * 0.22, (pose.index, 'shine')),
                  '#ffe08a', fill=True, alpha=0.55)
    for prints in range(3):  # thumbprints, pressed in fresh each shot
        r = random.Random(f'print:{pose.index}:{prints}')
        demo.dot(cv, r.uniform(-0.5, 0.5) * rx, r.uniform(0, 0.6) * ry, r.uniform(3, 5.5), CLAY_DARK, alpha=0.35)
    for side in (-1, 1):
        demo.dot(cv, side * 15, -ry * 0.22, 6.5, '#141414')
        demo.dot(cv, side * 15 + 2, -ry * 0.22 - 2.5, 2, '#ffffff')
    cv.arc(0, -ry * 0.02, 8, 0.25 * math.pi, 0.75 * math.pi, '#141414', width=2.5)
    c.restore()
    cv.mark('puppet', x - rx, cy - ry, 2 * rx, 2 * ry + 15 + hop)


def draw(n, cv):
    ground = demo.H - 120
    demo.floor(cv, ground)
    pose = stop_motion(n / demo.FPS, rate=10, seed=3)
    p = demo.phase(pose.t * demo.FPS, 0.2, 2.8)
    x = 200 + (demo.W - 400) * p
    hop = 60 * abs(math.sin(3 * math.pi * p))  # three hops across the stage
    _puppet(cv, x, ground, hop, pose)


TECHNIQUE = Technique(
    id='stop-motion-animation',
    name='Stop-motion animation',
    family='shapes',
    group='Hand-drawn & traditional',
    aliases=('stop motion', 'claymation', 'clay animation', 'object animation', 'puppet animation'),
    definition='Movement built from a handful of held poses a second, each set down by hand a little '
               'differently, so the subject steps along with a choppy, homemade wobble like a clay puppet.',
    phrasings=('make it move like a claymation figure',
               'animate it choppy and handmade, as if it were shot one frame at a time',
               'give it that jerky puppet-on-a-tabletop feel'),
    related=('interruptible-motion', 'delay', 'steps-easing', 'on-ones-on-twos-on-threes', 'hold',
             'moving-hold'),
    api=('videobuilder.techniques.shapes.stop_motion_animation.stop_motion',
         'videobuilder.techniques.shapes.stop_motion_animation.lumpy'),
    demo=lambda: demo.film(draw),
)
