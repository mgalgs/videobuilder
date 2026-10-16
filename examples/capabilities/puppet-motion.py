"""Capability: puppet motion. One cut-out picture of a cartoon fox, alive
through transforms alone: it breathes, sways and bobs, then crouches, hops,
stretches, squashes on landing and settles -- no new drawing, every move
pivoting on its feet.

    python -m videobuilder preview examples/capabilities/puppet-motion.py

LOOP = True: the breath runs two whole periods and the sway one across the
film, and the hop starts and ends at rest, so the last frame leads straight
into the first.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import text  # noqa: E402

LOOP = True
FPS = 30
TOTAL = 120          # 4.0 s

ANTIC = (30, 42)     # crouch and lean back
LAUNCH = (45, 49)    # crouch -> stretch, still grounded
LAND = 71            # airborne from LAUNCH[1] to here
SETTLE_SPRING = vb.damped(0.25, hz=2.4)

REST = (1.0, 1.0)
CROUCH = (1.10, 0.86)
STRETCH = (0.90, 1.16)
SQUASH = (1.16, 0.84)

HEIGHT = 360
HOP = 104
GROUND_Y = 600
BREATH = 60          # frames a breath; divides TOTAL

FOX = vb.Puppet({'idle': _kit.ASSETS / 'fox' / 'idle.png'}, height=HEIGHT)

TITLE_F = _kit.font(32, 700)


def mix(a, b, t):
    return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t


def hop_scale(n):
    """The hop's squash and stretch, (sx, sy); REST outside the hop."""
    if n < ANTIC[0]:
        return REST
    if n < ANTIC[1]:
        return mix(REST, CROUCH, vb.ease_in_out_quart((n - ANTIC[0]) / (ANTIC[1] - ANTIC[0])))
    if n < LAUNCH[0]:
        return CROUCH
    if n < LAUNCH[1]:
        return mix(CROUCH, STRETCH, vb.ease_in_out_quart((n - LAUNCH[0]) / (LAUNCH[1] - LAUNCH[0])))
    if n < LAND:
        p = (n - LAUNCH[1]) / (LAND - LAUNCH[1])
        if p < 0.35:
            return mix(STRETCH, REST, vb.ease_out_quint(p / 0.35))
        if p < 0.8:
            return REST
        return mix(REST, (0.94, 1.08), vb.ease_in_out_quart((p - 0.8) / 0.2))   # reaching down for the ground
    sp = vb.spring_at(n - LAND, FPS, **SETTLE_SPRING)
    return mix(SQUASH, REST, sp)


def air(n):
    """0..1 through the airborne span, or None on the ground."""
    if LAUNCH[1] <= n < LAND:
        return (n - LAUNCH[1]) / (LAND - LAUNCH[1])
    return None


def idle_weight(n):
    """How much of the idle sway and bob shows: none from the crouch to the settle."""
    a = vb.interpolate(n, [ANTIC[0] - 8, ANTIC[0]], [1, 0], ease=vb.ease_in_out_quart)
    b = vb.interpolate(n, [LAND + 18, LAND + 40], [0, 1], ease=vb.ease_in_out_quart)
    return a if n < LAND else b


def pose_at(n):
    """(sx, sy, lift, lean, angle) of the fox at frame n."""
    bx, by = FOX.breath(n, BREATH, depth=0.014)
    hx, hy = hop_scale(n)
    w = idle_weight(n)
    phase = 2 * math.pi * n / TOTAL
    sway = 0.03 * math.sin(phase) * w
    bob = 0.012 * (1 - math.cos(2 * phase)) / 2 * w   # a little dip at each end of the sway
    lean = sway
    if ANTIC[0] <= n < LAUNCH[1]:   # leans back into the crouch, springs upright on launch
        back = vb.interpolate(n, [ANTIC[0], ANTIC[1], LAUNCH[0], LAUNCH[1]], [0, -0.05, -0.05, 0.02],
                              ease=vb.ease_in_out_quart)
        lean += back
    p = air(n)
    lift = HOP * 4 * p * (1 - p) if p is not None else 0.0
    angle = math.radians(5) * math.sin(math.pi * p) * (1 - 2 * p) if p is not None else 0.0
    return bx * hx, by * hy * (1 - bob), lift, lean, angle


def draw(n, cv):
    cv.fill(_kit.BG)
    s = _kit.safe(cv, 64)
    _kit.text_marked(cv, 'title', text.wrap('Puppet motion', TITLE_F, s.w), TITLE_F, s.x, s.y, _kit.INK)
    cv.line(s.x, GROUND_Y, s.right, GROUND_Y, _kit.LINE, width=2)
    _kit.label(cv, 'caption', 'One cut-out picture, moved in code', s.x, GROUND_Y + 18)

    sx, sy, lift, lean, angle = pose_at(n)
    k = 1 - 0.45 * lift / HOP   # the shadow shrinks and fades as the fox leaves the ground
    cv.ctx.save()
    cv.ctx.translate(s.cx, GROUND_Y + 2)
    cv.ctx.scale(150 * k * sx, 14 * k)
    cv.ctx.arc(0, 0, 1, 0, 2 * math.pi)
    cv.ctx.set_source_rgba(0, 0, 0, 0.45 * k)
    cv.ctx.fill()
    cv.ctx.restore()

    FOX.draw(cv, 'idle', s.cx, GROUND_Y - lift, sx=sx, sy=sy, lean=lean, angle=angle, mark='fox')


FILM = vb.Film(draw=draw, fps=FPS, frames=TOTAL, formats=(_kit.FORMAT,), background=_kit.BG,
               keyframes=((0, 'rest'), (43, 'crouch'), (60, 'air'), (LAND, 'land'), (110, 'settled')))

if __name__ == '__main__':
    vb.main(__file__)
