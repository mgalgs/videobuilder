"""Capability: character motion. A blob hops in place -- anticipation,
launch stretch, an airborne arc, landing squash, and a springy
follow-through -- the full animator's-handbook vocabulary, timed in frames.

    python -m videobuilder preview examples/capabilities/character-motion.py

LOOP = True: the shape is at rest (1x1, on the ground, centred) at both the
very first and the very last frame, with the whole hop happening in between,
so the two ends match trivially.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import text  # noqa: E402

LOOP = True
FPS = 30

ANTIC_DUR = 11       # crouch pull-back
HOLD_DUR = 3         # hold the crouch
LAUNCH_DUR = 5       # crouch -> stretch, still grounded
AIR_LEN = 25         # airborne
SETTLE = 40          # follow-through after landing
TAIL = 16            # rest before the loop seam

HOLD_END = ANTIC_DUR + HOLD_DUR          # 14
AIR_START = HOLD_END + LAUNCH_DUR        # 19
LAND = AIR_START + AIR_LEN               # 44
TOTAL = LAND + SETTLE + TAIL             # 100, 3.33 s

REST = (1.0, 1.0)
CROUCH = (1.2, 0.75)
STRETCH = (0.85, 1.28)
SQUASH = (1.25, 0.70)
SETTLE_SPRING = vb.damped(0.22, hz=2.2)

BASE = 120
AIR_HEIGHT = 160
ARC_AMP = 0.10 * AIR_HEIGHT
GROUND_Y = 480

TITLE_F = _kit.font(32, 700)


def scale_at(n):
    if n < ANTIC_DUR:
        return (vb.interpolate(n, [0, ANTIC_DUR], [REST[0], CROUCH[0]], ease=vb.ease_in_out_quart),
                vb.interpolate(n, [0, ANTIC_DUR], [REST[1], CROUCH[1]], ease=vb.ease_in_out_quart))
    if n < HOLD_END:
        return CROUCH
    if n < AIR_START:
        t = n - HOLD_END
        return (vb.interpolate(t, [0, LAUNCH_DUR], [CROUCH[0], STRETCH[0]], ease=vb.ease_in_out_quart),
                vb.interpolate(t, [0, LAUNCH_DUR], [CROUCH[1], STRETCH[1]], ease=vb.ease_in_out_quart))
    if n < LAND:
        p = (n - AIR_START) / AIR_LEN
        if p < 0.3:
            q = p / 0.3
            return (vb.interpolate(q, [0, 1], [STRETCH[0], REST[0]], ease=vb.ease_out_quint),
                    vb.interpolate(q, [0, 1], [STRETCH[1], REST[1]], ease=vb.ease_out_quint))
        if p < 0.75:
            return REST
        q = (p - 0.75) / 0.25
        return (vb.interpolate(q, [0, 1], [REST[0], SQUASH[0]], ease=vb.ease_in_out_quart),
                vb.interpolate(q, [0, 1], [REST[1], SQUASH[1]], ease=vb.ease_in_out_quart))
    f = n - LAND
    sp = vb.spring_at(f, FPS, **SETTLE_SPRING)
    return (SQUASH[0] + (REST[0] - SQUASH[0]) * sp, SQUASH[1] + (REST[1] - SQUASH[1]) * sp)


def lift_at(n):
    if n < AIR_START or n >= LAND:
        return 0.0
    p = (n - AIR_START) / AIR_LEN
    return AIR_HEIGHT * 4 * p * (1 - p)


def arc_dx(n):
    if n < AIR_START or n >= LAND:
        return 0.0
    p = (n - AIR_START) / AIR_LEN
    return ARC_AMP * 4 * p * (1 - p)


def draw(n, cv):
    cv.fill(_kit.BG)
    s = _kit.safe(cv, 64)
    _kit.text_marked(cv, 'title', text.wrap('Character motion', TITLE_F, s.w), TITLE_F, s.x, s.y, _kit.INK)

    cv.line(s.x, GROUND_Y, s.right, GROUND_Y, _kit.LINE, width=2)

    sx, sy = scale_at(n)
    w, h = BASE * sx, BASE * sy
    cx = s.cx + arc_dx(n)
    bottom = GROUND_Y - lift_at(n)
    x, y = cx - w / 2, bottom - h
    cv.rect(x, y, w, h, _kit.ACCENT, radius=min(w, h) / 2)
    cv.mark('blob', x, y, w, h)


FILM = vb.Film(draw=draw, fps=FPS, frames=TOTAL, formats=(_kit.FORMAT,), background=_kit.BG,
               keyframes=((0, 'rest'), (12, 'crouch'), (31, 'peak'), (44, 'land'), (95, 'settled')))

if __name__ == '__main__':
    vb.main(__file__)
