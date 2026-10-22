"""Gravity Drop: an object let go from rest falls under constant acceleration,
covering more ground every frame until it reaches the floor."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def gravity_drop(t, start, end, duration):
    """Position at `t` seconds of something released from rest at `start` that
    falls under constant acceleration and reaches `end` at `duration` seconds:
    `start` for t <= 0, `end` for t >= duration, distance growing as t squared
    in between. `start`/`end` are any coordinate (a y, a scale, an angle)."""
    p = vb.clamp01(t / duration)
    return start + (end - start) * p * p


START, FALL = 0.5, 1.1  # released at 0.5 s, on the floor 1.1 s later
TICK = 0.1              # one ghost every 0.1 s: equal time apart, ever wider apart in space


def draw(n, cv):
    r, ground = 40, demo.H - 120
    top, rest = 110 + r, ground - r
    cx = demo.W / 2
    t = n / demo.FPS - START
    cv.outline(cx - r, top - r, 2 * r, 2 * r, demo.MUTED, width=2, radius=r, alpha=0.4)  # where it was let go
    demo.floor(cv, ground)
    k = 1
    while k * TICK < min(t, FALL):  # the strobe: where it was at each tick so far
        gy = gravity_drop(k * TICK, top, rest, FALL)
        demo.dot(cv, cx, gy, 7, color=demo.TEAL, alpha=0.7)
        cv.line(cx - r - 70, gy, cx - r - 30, gy, demo.TEAL, width=4)
        k += 1
    y = gravity_drop(t, top, rest, FALL)
    demo.dot(cv, cx, y, r)
    cv.mark('ball', cx - r, y - r, 2 * r, 2 * r)


TECHNIQUE = Technique(
    id='gravity-drop',
    name='Gravity Drop',
    family='principles',
    group='Physics',
    aliases=('free fall', 'gravitational acceleration', 'ease in quad'),
    definition='Something is let go and falls straight down, starting slowly and picking up speed '
               'steadily, as if gravity were pulling it.',
    phrasings=('drops from the top and speeds up as it falls',
               'let it fall like a real object would',
               'have it free-fall onto the floor'),
    related=('physics-letter-drop', 'character-drop', 'sub-drop', 'falling-leaves',
             'gravity-well-attraction', 'momentum-fling'),
    api=('videobuilder.techniques.principles.gravity_drop.gravity_drop',),
    demo=lambda: demo.film(draw),
)
