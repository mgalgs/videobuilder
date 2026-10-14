"""Capability: springs with character. The same spring drop at three damping
ratios, landing side by side, so the difference between a firm settle and a
playful bounce is visible rather than described.

    python -m videobuilder preview examples/capabilities/springs-with-character.py

LOOP = True: each circle drops in, holds, then eases back out above the
frame, so both ends of the clip are the same "not yet dropped" rest state.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import fr, text  # noqa: E402

LOOP = True
FPS = 30
TOTAL = 90          # 3.0 s
LEAVE_START, LEAVE = 64, 18

RINGS = (
    ('1.0', 'Firm', vb.damped(1.0, hz=2.0)),
    ('0.6', 'Restrained', vb.damped(0.6, hz=2.0)),
    ('0.3', 'Playful', vb.damped(0.3, hz=2.0)),
)

R = 46
DROP = 480
TITLE_F = _kit.font(32, 700)
NAME_F = _kit.font(22, 650)
RATIO_F = _kit.font(17, 500, family=_kit.MONO)


def circle_y(params, n, rest_y):
    if n < LEAVE_START:
        s = vb.spring_at(n, FPS, **params)
        return rest_y - DROP * (1 - s)
    lp = min(1.0, (n - LEAVE_START) / LEAVE)
    return rest_y - DROP * vb.ease_in_expo(lp)


def draw(n, cv):
    cv.fill(_kit.BG)
    s = _kit.safe(cv, 64)
    _kit.text_marked(cv, 'title', text.wrap('Springs with character', TITLE_F, s.w), TITLE_F, s.x, s.y, _kit.INK)
    cols = s.pad(140, 0, 0, 0).row(fr, fr, fr, gap=0)
    rest_y = s.y + 360
    for col, (ratio, name, params) in zip(cols, RINGS):
        cx = col.cx
        y = circle_y(params, n, rest_y)
        if y + R > 0:   # only draw/mark once some part of it has entered the frame
            cv.rect(cx - R, y - R, 2 * R, 2 * R, _kit.ACCENT, radius=R)
            if y - R >= 0:
                cv.mark(f'ball-{ratio}', cx - R, y - R, 2 * R, 2 * R)
        _kit.text_marked(cv, f'name-{ratio}', text.wrap(name, NAME_F, col.w), NAME_F,
                         col.x, rest_y + R + 28, _kit.INK, align='center', width=col.w)
        _kit.text_marked(cv, f'ratio-{ratio}', text.wrap(f'ratio {ratio}', RATIO_F, col.w), RATIO_F,
                         col.x, rest_y + R + 60, _kit.MUTED, align='center', width=col.w)
    floor_y = rest_y + R + 10
    cv.line(s.x, floor_y, s.right, floor_y, _kit.LINE, width=2)


FILM = vb.Film(draw=draw, fps=FPS, frames=TOTAL, formats=(_kit.FORMAT,), background=_kit.BG,
               keyframes=((40, 'settled'), (80, 'leaving')))

if __name__ == '__main__':
    vb.main(__file__)
