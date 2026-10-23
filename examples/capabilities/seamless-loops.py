"""Capability: seamless loops, shown literally. A dot orbits a ring, driven
purely by a wrapping phase (`n % PERIOD / PERIOD`) fed into `math.sin`/`cos`
-- no enter, no exit, no hidden cut. The ring itself traces the dot's full
path and a readout shows the phase value, so the capability is legible, not
just pretty.

    python -m videobuilder preview examples/capabilities/seamless-loops.py

LOOP = True: continuous throughout, by construction -- frame 0 and the frame
just past the last are the same point in the cycle.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import text  # noqa: E402

LOOP = True
PERIOD = 90   # 3.0 s true period at 30 fps

TITLE_F = _kit.font(32, 700)
CAPTION_F = _kit.font(22, 600)
PHASE_F = _kit.font(22, 500, family=_kit.MONO)

RING_R = 190
DOT_R = 14


def draw(n, cv):
    cv.fill(_kit.BG)
    s = _kit.safe(cv, 64)
    _kit.text_marked(cv, 'title', text.wrap('Seamless loops', TITLE_F, s.w), TITLE_F, s.x, s.y, _kit.INK)

    phase = (n % PERIOD) / PERIOD   # wraps 0..1 .. 0, a true period
    cx, cy = s.cx, s.y + 300
    ang = 2 * math.pi * phase - math.pi / 2   # start at the top

    cv.arc(cx, cy, RING_R, 0, 2 * math.pi, _kit.LINE, width=2)   # the orbit path, a thin stroke (unmarked, like a gridline)

    dx, dy = cx + RING_R * math.cos(ang), cy + RING_R * math.sin(ang)
    cv.line(cx, cy, dx, dy, _kit.LINE, width=1)
    cv.rect(dx - DOT_R, dy - DOT_R, 2 * DOT_R, 2 * DOT_R, _kit.ACCENT, radius=DOT_R)
    cv.mark('dot', dx - DOT_R, dy - DOT_R, 2 * DOT_R, 2 * DOT_R)

    phase_text = f'phase {phase:.2f}'
    pw, ph = text.block_size([phase_text], PHASE_F)
    _kit.text_marked(cv, 'phase', [phase_text], PHASE_F, cx - pw / 2, cy - ph / 2, _kit.MUTED,
                      align='center', width=pw)

    cap = text.wrap('Seamless — driven by a wrapping phase, not a hidden cut', CAPTION_F, s.w)
    cw, ch = text.block_size(cap, CAPTION_F)
    _kit.text_marked(cv, 'caption', cap, CAPTION_F, s.cx - cw / 2, s.bottom - ch, _kit.MUTED,
                      align='center', width=s.w)


FILM = vb.Film(draw=draw, fps=30, frames=PERIOD, formats=(_kit.FORMAT,), background=_kit.BG,
               keyframes=(0, PERIOD // 4, PERIOD // 2, 3 * PERIOD // 4))

if __name__ == '__main__':
    vb.main(__file__)
