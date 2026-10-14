"""Capability: pop on the beat. A chip takes a quick scale accent exactly on
each beat of a silent visual grid -- the grid-locked punctuation a logo or a
stat gets on a cut. (A separate "beat lock" demo elsewhere in the catalog
puts real audio under a different visual; this one stays silent so the two
don't duplicate each other.)

    python -m videobuilder preview examples/capabilities/pop-on-the-beat.py

LOOP = True: the motion is a true period, not an enter/exit. Six beats make
one 3.0 s cycle; each pop has fully decayed back to baseline well inside its
beat, so frame 0 (itself mid-pop, on beat 0) continues the rhythm exactly as
the next cycle's beat 0 would.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import text  # noqa: E402

LOOP = True
FPS = 30
GRID = _kit.grid(bpm=120)          # 15 frames/beat
LOOP_BEATS = 6
TOTAL = GRID.b(LOOP_BEATS)         # 90 frames, 3.0 s

POP = vb.damped(0.45, hz=5.0)      # quick, with a small bounce back through baseline
AMOUNT = 0.16
CHIP = 150
DOT_R = 7
DOT_GAP = 30

TITLE_F = _kit.font(32, 700)


def beat_of(n):
    """The most recent beat at or before frame n."""
    return max(b for b in range(LOOP_BEATS) if GRID.b(b) <= n)


def draw(n, cv):
    cv.fill(_kit.BG)
    s = _kit.safe(cv, 64)
    _kit.text_marked(cv, 'title', text.wrap('Pop on the beat', TITLE_F, s.w), TITLE_F, s.x, s.y, _kit.INK)

    k = beat_of(n)
    offset = n - GRID.b(k)
    decay = vb.spring_at(offset, FPS, **POP)    # 0 right on the beat, -> 1 as it settles
    scale = 1 + AMOUNT * (1 - decay)
    w = h = CHIP * scale
    cx, cy = s.cx, s.cy - 20
    cv.rect(cx - w / 2, cy - h / 2, w, h, _kit.ACCENT, radius=min(w, h) * 0.28)
    cv.mark('chip', cx - w / 2, cy - h / 2, w, h)

    dots_w = (LOOP_BEATS - 1) * DOT_GAP
    y = cy + CHIP / 2 + 56
    for i in range(LOOP_BEATS):
        x = s.cx - dots_w / 2 + i * DOT_GAP
        lit = max(0.0, 1 - decay) if i == k else 0.0
        color = _kit.TEAL if lit > 0.5 else _kit.LINE
        cv.rect(x - DOT_R, y - DOT_R, 2 * DOT_R, 2 * DOT_R, color, radius=DOT_R)
    cv.mark('beat-dots', s.cx - dots_w / 2 - DOT_R, y - DOT_R, dots_w + 2 * DOT_R, 2 * DOT_R)


FILM = vb.Film(draw=draw, fps=FPS, frames=TOTAL, formats=(_kit.FORMAT,), background=_kit.BG,
               keyframes=((0, 'on the beat'), (7, 'between beats'), (15, 'next beat')))

if __name__ == '__main__':
    vb.main(__file__)
