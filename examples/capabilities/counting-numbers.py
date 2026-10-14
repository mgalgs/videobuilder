"""Capability: numbers that count up. A hero stat counts from zero to its
final value on a spring, then holds, then fades for the loop.

    python -m videobuilder preview examples/capabilities/counting-numbers.py

LOOP = True: the stat fades out before the seam and back in after it, so the
loop crosses on a matching near-invisible frame at both ends.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import text  # noqa: E402

LOOP = True
GRID = _kit.grid(bpm=120)
TIMELINE = vb.Timeline(GRID, [vb.Segment('loop', 0, 8)], end=8)   # 4.0 s

VALUE = 2.4
LABEL = 'faster than the baseline'

ENTER = 36
FADE = 16
HOLD_END = 90          # fully visible through here
TOTAL = 120

NUMBER_F = _kit.font(128, 700, family=_kit.MONO)
LABEL_F = _kit.font(24, 600)


def alpha(n):
    if n < FADE:
        return n / FADE
    if n > TOTAL - FADE:
        return (TOTAL - n) / FADE
    return 1.0


def draw(n, cv):
    cv.fill(_kit.BG)
    s = _kit.safe(cv, 64)
    p = vb.interpolate(n, [0, ENTER], [0, 1], ease=vb.ease_out_expo)
    shown = f'{VALUE * p:.1f}x'
    a = alpha(n)
    number_lines = text.wrap(shown, NUMBER_F, s.w)
    nw, nh = text.block_size(number_lines, NUMBER_F)
    label_lines = text.wrap(LABEL, LABEL_F, s.w)
    lw, lh = text.block_size(label_lines, LABEL_F)
    total_h = nh + 18 + lh
    top = s.cy - total_h / 2
    text.draw(cv, number_lines, NUMBER_F, s.cx - nw / 2, top, _kit.INK, alpha=a)
    cv.mark('value', s.cx - nw / 2, top, nw, nh)
    text.draw(cv, label_lines, LABEL_F, s.cx - lw / 2, top + nh + 18, _kit.MUTED, alpha=a)
    cv.mark('label', s.cx - lw / 2, top + nh + 18, lw, lh)


FILM = vb.Film(draw=draw, timeline=TIMELINE, formats=(_kit.FORMAT,), background=_kit.BG,
               keyframes=((ENTER + 10, 'counted'), (60, 'held')))

if __name__ == '__main__':
    vb.main(__file__)
