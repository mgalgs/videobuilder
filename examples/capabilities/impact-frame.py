"""Capability: impact frame. The anime hit, punctuating one moment: the fox
crouches, leaps and lands, and the landing hits -- a fast push-in, two held
frames of the fox as a flat silhouette in a burst of speed lines on white,
then the picture again, shaking and settling while the speed lines linger
and fade (`vb.impact.Hit`).

    python -m videobuilder preview examples/capabilities/impact-frame.py

One full-frame flash in the whole film, never a strobe.

LOOP = True: the fox stands at rest, breathing, at both ends, and the
breath runs two whole periods.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import impact, text  # noqa: E402

LOOP = True
GRID = _kit.grid()
FPS = GRID.fps
FPB = round(GRID.frames_per_beat)
TOTAL = 8 * FPB           # 4.0 s
BREATH = 60

CROUCH = (2 * FPB - 6, 2 * FPB + 4)   # 24..34: crouch, then spring up
LAND = 4 * FPB                        # 60: the hit, on beat 5
HOP = 170
HIT = impact.Hit(at=LAND, seed=3)
LAND_SPRING = vb.damped(0.3, hz=2.4)

GROUND_Y = 560
FOX = vb.Puppet({name: _kit.ASSETS / 'fox' / f'{name}.png' for name in ('idle', 'cheer', 'surprised')}, height=300)

TITLE_F = _kit.font(32, 700)


def body_at(n):
    """(pose, sx, sy, lift) at frame n."""
    sx, sy = FOX.breath(n, BREATH)
    if n < CROUCH[0]:
        return 'idle', sx, sy, 0.0
    if n < CROUCH[1]:
        p = vb.interpolate(n, [CROUCH[0], CROUCH[1] - 3, CROUCH[1]], [0, 1, 0], ease=vb.ease_in_out_quart)
        return 'idle', sx * (1 + 0.1 * p), sy * (1 - 0.14 * p), 0.0
    if n < LAND:
        p = (n - CROUCH[1]) / (LAND - CROUCH[1])
        stretch = 1 + 0.12 * (1 - min(1, p * 3)) + 0.08 * max(0, p - 0.75) * 4   # off the ground, and reaching down
        return 'cheer', sx / math.sqrt(stretch), sy * stretch, HOP * 4 * p * (1 - p)
    sp = vb.spring_at(n - LAND, FPS, **LAND_SPRING)
    pose = 'surprised' if n < LAND + 12 else 'idle'
    return pose, sx * (1.16 - 0.16 * sp), sy * (0.84 + 0.16 * sp), 0.0


def fox(cv, n):
    pose, sx, sy, lift = body_at(n)
    FOX.draw(cv, pose, cv.width / 2, GROUND_Y - lift, sx=sx, sy=sy, mark='fox')


def scene(cv, n):
    cv.fill(_kit.BG)
    s = _kit.safe(cv, 64)
    cv.line(s.x, GROUND_Y, s.right, GROUND_Y, _kit.LINE, width=2)
    _kit.label(cv, 'caption', 'The fox lands the jump', s.x, GROUND_Y + 18)
    _, _, _, lift = body_at(n)
    k = 1 - 0.5 * lift / HOP
    ctx = cv.ctx
    ctx.save()
    ctx.translate(cv.width / 2, GROUND_Y + 2)
    ctx.scale(130 * k, 12 * k)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.set_source_rgba(0, 0, 0, 0.45 * k)
    ctx.fill()
    ctx.restore()
    fox(cv, n)


def draw(n, cv):
    HIT.draw(cv, n, lambda c: scene(c, n), lambda c: fox(c, n), centre=(cv.width / 2, GROUND_Y - 110))
    s = _kit.safe(cv, 64)   # the title holds still through the push-in and the shake
    _kit.text_marked(cv, 'title', text.wrap('Impact frame', TITLE_F, s.w), TITLE_F, s.x, s.y, _kit.INK)


FILM = vb.Film(draw=draw, fps=FPS, frames=TOTAL, formats=(_kit.FORMAT,), background=_kit.BG,
               keyframes=((10, 'rest'), (30, 'crouch'), (63, 'shaking'), (100, 'settled')))

if __name__ == '__main__':
    vb.main(__file__)
