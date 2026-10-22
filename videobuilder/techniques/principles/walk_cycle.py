"""Walk Cycle: a figure's legs and arms run through one repeating stride --
contact, down, passing, up, then the same on the other side -- so that
looping it, with the ground sliding past, reads as walking."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

# Body proportions as shares of the figure's height (feet to top of head).
THIGH, SHIN, FOOT, HEEL = 0.245, 0.245, 0.085, 0.025
TORSO, NECK, HEAD = 0.30, 0.035, 0.075
UPPER_ARM, FOREARM = 0.165, 0.155


def _smooth(u):
    u = vb.clamp01(u)
    return u * u * (3 - 2 * u)


def _leg(phase, step):
    """One leg at `phase` (0 -> 1 through a full cycle, 0 its heel strike), in
    height units with the hip at (0, 0) and y down: (knee, ankle, heel, toe).
    In stance (the first half) the ankle slides back at a constant speed, so
    a ground moving at that speed never slips under the foot."""
    d = step / 2
    if phase < 0.5:                                          # stance: planted, pushed back
        x = d * (1 - 4 * phase)
        knee = math.radians(16) * math.sin(math.pi * min(phase / 0.3, 1.0))   # gives a little on the down
        if phase < 0.1:
            pitch = 0.3 * (1 - phase / 0.1)                  # heel strike, toe up, rolling flat
        elif phase < 0.35:
            pitch = 0.0
        else:
            pitch = -0.7 * (phase - 0.35) / 0.15             # heel peels off, toe pushes
    else:                                                    # swing: lifted, carried forward
        u = (phase - 0.5) / 0.5
        x = -d + 2 * d * _smooth(u)
        knee = math.radians(62) * math.sin(math.pi * u)
        pitch = -0.7 + 1.0 * _smooth(u)
    chord = math.sqrt(THIGH ** 2 + SHIN ** 2 + 2 * THIGH * SHIN * math.cos(knee))
    thigh = math.asin(max(-1.0, min(1.0, x / chord))) + knee / 2   # from straight down, + is forward
    kx, ky = THIGH * math.sin(thigh), THIGH * math.cos(thigh)
    ax, ay = kx + SHIN * math.sin(thigh - knee), ky + SHIN * math.cos(thigh - knee)
    c, s = math.cos(pitch), math.sin(pitch)
    return (kx, ky), (ax, ay), (ax - HEEL * c, ay + HEEL * s), (ax + FOOT * c, ay - FOOT * s)


def walk_pose(phase, step=0.4, arm_swing=1.5, lean=0.06):
    """The figure at `phase` of a walk cycle (0 -> 1 is two steps; 0 is the
    near leg's heel strike, 0.5 the far leg's), facing +x. Returns a dict of
    joints in height units, x from the hip and y up from the ground (0) as a
    negative number, ready to scale: 'hip', 'neck', 'head' (centre), and
    'near'/'far' each with 'knee', 'ankle', 'heel', 'toe', 'shoulder',
    'elbow', 'hand'. The hip rises and falls on its own, from whichever foot
    is lowest. Each half cycle the ground moves back `step` (height units),
    so scroll the scene at `2 * step * height` px per cycle."""
    legs = {'near': _leg(phase % 1.0, step), 'far': _leg((phase + 0.5) % 1.0, step)}
    lowest = max(p[1] for leg in legs.values() for p in leg[1:])
    out = {'hip': (0.0, -lowest)}
    sx, sy = TORSO * math.sin(lean), -lowest - TORSO * math.cos(lean)
    out['neck'] = (sx, sy)
    out['head'] = (sx + (NECK + HEAD) * math.sin(lean), sy - NECK - HEAD)
    for side, (knee, ankle, heel, toe) in legs.items():
        hip_swing = math.asin(max(-1.0, min(1.0, (ankle[0] / (THIGH + SHIN)))))
        arm = -arm_swing * hip_swing                          # each arm swings against its own leg
        elbow_bend = 0.25 + 0.5 * max(0.0, math.sin(arm))
        ex, ey = sx + UPPER_ARM * math.sin(arm), sy + UPPER_ARM * math.cos(arm)
        hx, hy = ex + FOREARM * math.sin(arm + elbow_bend), ey + FOREARM * math.cos(arm + elbow_bend)
        lift = lambda p: (p[0], p[1] - lowest)               # noqa: E731 -- hip-relative -> ground-relative
        out[side] = {'knee': lift(knee), 'ankle': lift(ankle), 'heel': lift(heel), 'toe': lift(toe),
                     'shoulder': (sx, sy), 'elbow': (ex, ey), 'hand': (hx, hy)}
    return out


def _stroke(cv, pts, color, width, alpha=1.0):
    c = cv.ctx
    c.save()
    c.new_path()
    c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    c.set_line_cap(1)    # cairo.LINE_CAP_ROUND
    c.set_line_join(1)   # cairo.LINE_JOIN_ROUND
    c.set_line_width(width)
    c.set_source_rgba(*vb.canvas.rgba(color, alpha))
    c.stroke()
    c.restore()


def draw_walker(cv, x, ground, height, phase, color=demo.INK, near=demo.ACCENT, far=demo.MUTED,
                facing=1, mark=None, **kw):
    """Draw a stick figure `height` px tall at `phase` of a walk cycle, its
    hip above `x` and its feet on the line y = `ground`; `facing` -1 walks
    left. The far limbs are drawn first in `far`, the near ones over the body
    in `near`. `kw` goes to `walk_pose`. Returns its Box (also `cv.mark`ed as
    `mark`, if given)."""
    pose = walk_pose(phase, **kw)
    at = lambda p: (x + facing * p[0] * height, ground + p[1] * height)   # noqa: E731
    w = 0.045 * height
    hip, neck = at(pose['hip']), at(pose['neck'])

    def limbs(side, color):
        j = pose[side]
        _stroke(cv, [at(j['shoulder']), at(j['elbow']), at(j['hand'])], color, w * 0.85)
        _stroke(cv, [hip, at(j['knee']), at(j['ankle']), at(j['heel']), at(j['toe'])], color, w)

    limbs('far', far)
    _stroke(cv, [hip, neck], color, w * 1.25)
    hx, hy = at(pose['head'])
    demo.dot(cv, hx, hy, HEAD * height, color=color)
    limbs('near', near)
    box = vb.Box(x - 0.35 * height, ground - height, 0.7 * height, height)
    if mark:
        cv.mark(mark, *box)
    return box


CYCLE = 30   # frames for two steps
HEIGHT, STEP = 340, 0.4


def draw(n, cv):
    ground = demo.H - 80
    phase = n / CYCLE
    # The ground slides back exactly as fast as the planted foot, so the figure walks on the spot.
    scroll = (phase * 2 * STEP * HEIGHT) % 80
    demo.floor(cv, ground)
    for i in range(-1, demo.W // 80 + 2):
        tx = i * 80 - scroll
        cv.line(tx, ground + 14, tx - 22, ground + 34, demo.LINE, width=4)
    cv.ctx.save()
    cv.ctx.translate(demo.W / 2, ground + 4)
    cv.ctx.scale(1, 0.12)
    demo.dot(cv, 0, 0, 70, color='#000000', alpha=0.35)
    cv.ctx.restore()
    draw_walker(cv, demo.W / 2, ground, HEIGHT, phase, step=STEP, mark='walker')


TECHNIQUE = Technique(
    id='walk-cycle',
    name='Walk Cycle',
    family='principles',
    group='Cycles & loops',
    aliases=('walk loop', 'walking cycle', 'gait cycle'),
    definition='A character steps through one full stride of legs and swinging arms that repeats '
               'seamlessly, so it keeps walking for as long as the loop runs.',
    phrasings=('make the character walk',
               'a little figure walking in place while the ground scrolls by',
               'loop a stride so the person keeps strolling along'),
    related=('geometric-loop', 'rotating-polygon-loop', 'steps-easing', 'cycle-diagram-rotation',
             'stop-motion-animation', 'pendulum-swing'),
    api=('videobuilder.techniques.principles.walk_cycle.draw_walker',
         'videobuilder.techniques.principles.walk_cycle.walk_pose',
         'videobuilder.Puppet.walk'),
    demo=lambda: demo.film(draw),
)
