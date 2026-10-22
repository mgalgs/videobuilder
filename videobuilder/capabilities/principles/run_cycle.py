"""Run Cycle: videobuilder already has it as `Stick.gait(n, 'run')`, which
returns each frame's pose, how far the body has travelled and how high it
is off the ground, so this entry only names it and demos it."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

FIG = vb.Stick(height=250, ink=demo.INK, fill=demo.BG, fps=demo.FPS)
GROUND = demo.H - 120
TICK = 120  # spacing of the ground marks that scroll by, so the run in place reads as moving


def draw(n, cv):
    step = FIG.gait(n, 'run')
    demo.floor(cv, GROUND)
    x = 80 - step.x % TICK
    while x < demo.W - 80:
        x0, x1 = max(x, 80), min(x + 40, demo.W - 80)
        if x1 > x0:
            cv.line(x0, GROUND + 14, x1, GROUND + 14, demo.MUTED, width=3, alpha=0.6)
        x += TICK
    vb.stick.shadow(cv, FIG, demo.W / 2, GROUND, k=1 - 0.4 * step.lift / max(FIG.height * 0.1, 1))
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
    api=('videobuilder.Stick.gait', 'videobuilder.Stick.draw'),
    demo=lambda: demo.film(draw),
)
