"""Stick figure: a figure drawn in code runs flat out into a brick wall on
beat 2, pushes, gives up and thinks, then turns and points back the other
way on beat 4 -- the explainer format's shorthand for "working harder isn't
moving forward", on paper, in the figure's own scene kit."""
from videobuilder import Stick, stick

from . import kit

FPB = kit.FPB
HIT, THINK, TURN, POINT = 2 * FPB, 3 * FPB, 4 * FPB - 6, 4 * FPB
PAPER = '#f4f1ea'
INK = '#16171b'

FIGS = {}


def _fig(st):
    key = st.name
    if key not in FIGS:
        FIGS[key] = Stick(height=kit.pick(st, 300, 340), ink=INK, fps=kit.FPS, seed=4)
    return FIGS[key]


def figure(cv, s, st):
    fig = _fig(st)
    n = s.f
    c = st.content
    ground = c.bottom - kit.pick(st, 40, 220)
    wall_x = c.cx + kit.pick(st, 260, 150)
    reach = fig.joints('push', 0, 0)['front_hand'][0] + 0.02 * fig.height
    stop = wall_x - reach
    x = stop - fig.speed('run') * (HIT - min(n, HIT))
    cv.fill(PAPER)
    stick.ground(cv, fig, ground, st.frame.x, st.frame.right)
    stick.wall(cv, fig, wall_x, ground, height=1.4)
    if n < HIT:
        pose = fig.gait(n, 'run').pose
        lift = fig.gait(n, 'run').lift
    else:
        pose = fig.act(n, [(0, 'run'), (HIT, 'push', 3), (THINK, 'think', 10), (POINT, 'point', 10)])
        lift = 0.0
    face = fig.face_at(n, [(0, 'determined'), (HIT + 6, 'annoyed', 4), (THINK, 'thinking'), (POINT, 'happy')])
    stick.shadow(cv, fig, x, ground, k=1 - lift / fig.height)
    fig.draw(cv, pose, x, ground - lift, face=face, facing=fig.turn(n, TURN, 6), blink=fig.blink(n), mark='stick')


SCENES = {'stick': figure}
