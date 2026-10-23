"""Run Cycle: a run gait tuned to read as running at a glance. Each foot
reaches far and is down for under a third of the cycle, so the figure spends
several frames of every step with both feet clearly off the ground, hips
risen, back leg stretched out behind from the push-off. `run(fig, n)`
returns a `vb.stick.Step` like `Stick.gait`, so it drops into any film that
draws a Stick."""
import math

import videobuilder as vb
from videobuilder import stick

from .. import _demo as demo
from ..schema import Capability

FIG = vb.Stick(height=250, ink=demo.INK, fill=demo.BG, fps=demo.FPS)
GROUND = demo.H - 120
PERIOD = 0.75   # seconds a cycle (two steps): four whole cycles in the 3 s demo, so the clip loops
DUTY = 0.3      # share of the cycle each foot is down; the rest of each step is flight
REACH = 0.65    # how far a foot lands ahead of the hip, and leaves behind it, as a share of the leg
HOP = 0.065     # how high the hips rise in flight, as a share of the height
TICK = 2 * REACH * stick.LEG * FIG.height / DUTY / 2   # ground-mark spacing: half what a cycle travels, so the clip loops


def run(fig, n, period=PERIOD, stride=1.0, start=0):
    """A Step (pose, x travelled, lift, phase, contact) for frame `n` of a
    run cycle from frame `start`: `period` seconds a cycle, `stride`
    scaling the reach. Each foot plants, pushes off with the leg straight
    out behind, and both feet are off the ground between steps."""
    T = period * fig.fps
    s = REACH * stick.LEG * stride
    stand = 0.97 * stick.LEG
    f = n - start
    phase = (f / T) % 1.0

    def foot(ph):
        ph %= 1.0
        if ph < DUTY:                                       # down: sliding back under the hip
            return s - 2 * s * ph / DUTY, 0.0, True
        u = (ph - DUTY) / (1 - DUTY)                         # up: heel kicks up, knee drives forward
        x = -s + 2 * s * vb.ease_in_out_quart(vb.clamp01((u - 0.12) / 0.88))
        lift = 0.45 * stick.LEG * math.sin(math.pi * min(1.0, u / 0.85)) ** 1.2
        return x, lift, False

    feet = {'front': foot(phase), 'back': foot(phase + 0.5)}
    down = [k for k, (_, _, d) in feet.items() if d]
    if down:
        h = min(math.sqrt(max(stand ** 2 - feet[k][0] ** 2, 0)) for k in down)
        air = 0.0
    else:                                                    # flight: the hips coast on an arc
        h = math.sqrt(stand ** 2 - s ** 2)
        u = ((phase - DUTY) % 0.5) / (0.5 - DUTY)
        air = HOP * 4 * u * (1 - u)
    targets = {k: (x, h - lift) for k, (x, lift, _) in feet.items()}
    sw = math.cos(2 * math.pi * phase)
    bob = math.sin(4 * math.pi * phase)
    pose = stick.Pose(lean=14, nod=-2 + 1.5 * bob,
                      front_arm=-55 * sw, front_elbow=80 + 24 * max(0.0, -sw),
                      back_arm=55 * sw, back_elbow=80 + 24 * max(0.0, sw),
                      **stick._legs_to(targets['front'], targets['back']))
    lowest = max(y for _, y in targets.values())
    lift = (h - lowest) * fig.height + air * fig.height
    speed = 2 * s * fig.height / (DUTY * T)
    contact = 'both' if len(down) == 2 else down[0] if down else None
    return stick.Step(pose, speed * f, lift, phase, contact)


def draw(n, cv):
    step = run(FIG, n, start=-2)   # puts the poster frame (70% in) at the top of a flight
    demo.floor(cv, GROUND)
    x = 80 - step.x % TICK
    while x < demo.W - 80:
        x0, x1 = max(x, 80), min(x + 40, demo.W - 80)
        if x1 - x0 >= 8:                                     # no slivers flickering at the floor's ends
            cv.line(x0, GROUND + 14, x1, GROUND + 14, demo.MUTED, width=3, alpha=0.6)
        x += TICK
    vb.stick.shadow(cv, FIG, demo.W / 2, GROUND, k=1 - 0.5 * min(1.0, step.lift / (HOP * FIG.height * 1.3)))
    FIG.draw(cv, step.pose, demo.W / 2, GROUND, face='happy', lift=step.lift, mark='runner')


CAPABILITY = Capability(
    id='run-cycle',
    name='Run Cycle',
    family='principles',
    group='Cycles & loops',
    aliases=('running loop', 'run loop', 'run in place'),
    definition='A short looping set of poses in which a figure pushes off, flies with both feet off the '
               'ground, lands and pushes off again, repeated so it seems to run without stopping.',
    phrasings=('make the character run',
               'a figure jogging on the spot while the ground slides past',
               'loop a running animation'),
    related=('rotating-polygon-loop', 'geometric-loop', 'cycle-diagram-rotation', 'staged-onboarding-walkthrough',
             'layout-animation-flip', 'interruptible-motion'),
    api=('videobuilder.capabilities.principles.run_cycle.run', 'videobuilder.Stick.draw', 'videobuilder.stick.shadow'),
    demo=lambda: demo.film(draw),
)
