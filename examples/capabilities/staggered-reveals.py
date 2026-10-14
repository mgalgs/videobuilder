"""Capability: staggered reveals. A short list cascades in, each item
starting while the one before it is still mid-flight, then leaves the same
way it came, row by row.

    python -m videobuilder preview examples/capabilities/staggered-reveals.py

LOOP = True: nothing is on screen at frame 0 or the last frame; the whole
cascade -- enter, hold, leave -- happens between those two empty rest states.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import text  # noqa: E402

LOOP = True
FPS = 30
TOTAL = 116          # 3.87 s

ITEMS = ('Plan', 'Shoot', 'Edit', 'Ship')

START = 8            # frames of rest before the first item starts entering
STAGGER = 6          # frames between one item's start and the next's (200 ms)
ENTER = 22           # frames for the position spring to settle
FADE_IN = 14         # frames for the opacity to reach 1
HOLD = 22            # frames all four sit still once the last one has landed
LEAVE = 18           # frames for the exit
FADE_OUT = 12

SPRING = vb.damped(0.62, hz=2.0)
DISP = 40            # px an item rises as it enters

LAST_ENTER_START = START + 3 * STAGGER
LEAVE_START = LAST_ENTER_START + ENTER + HOLD
LAST_LEAVE_END = LEAVE_START + 3 * STAGGER + LEAVE
assert LAST_LEAVE_END + 6 <= TOTAL, 'tail rest before the loop seam is too tight'

ROW_F = _kit.font(34, 650)
TITLE_F = _kit.font(32, 700)
DOT = 16
GAP = 22             # between the dot and the label


def item_state(i, n):
    """(dy, alpha) for item i at frame n. dy > 0 means still below rest."""
    enter_n = n - (START + i * STAGGER)
    if enter_n < 0:
        return DISP, 0.0
    leave_n = n - (LEAVE_START + i * STAGGER)
    if leave_n < 0:
        s = min(1.0, vb.spring_at(enter_n, FPS, **SPRING))
        dy = DISP * (1 - s)
        a = vb.interpolate(enter_n, [0, FADE_IN], [0, 1], ease=vb.ease_out_quint)
        return dy, a
    if leave_n < LEAVE:
        p = vb.interpolate(leave_n, [0, LEAVE], [0, 1], ease=vb.ease_in_expo)
        a = vb.interpolate(leave_n, [0, FADE_OUT], [1, 0], ease=vb.ease_in_expo)
        return DISP * p, max(0.0, a)
    return DISP, 0.0


def draw(n, cv):
    cv.fill(_kit.BG)
    s = _kit.safe(cv, 64)
    _kit.text_marked(cv, 'title', text.wrap('Staggered reveals', TITLE_F, s.w), TITLE_F, s.x, s.y, _kit.INK)

    row_lines = [text.wrap(word, ROW_F, s.w - DOT - GAP) for word in ITEMS]
    row_h = max(max(text.block_size(lines, ROW_F)[1] for lines in row_lines), DOT)
    rows, _ = s.pad(150, 0, 0, 0).stack([row_h] * len(ITEMS), gap=26)

    for i, (word, row, lines) in enumerate(zip(ITEMS, rows, row_lines)):
        dy, a = item_state(i, n)
        if a <= 0.01:
            continue
        y = row.y + dy
        cv.rect(row.x, y + (row_h - DOT) / 2, DOT, DOT, _kit.ACCENT, radius=DOT / 2, alpha=a)
        cv.mark(f'dot-{word}', row.x, y + (row_h - DOT) / 2, DOT, DOT)
        tw, th = text.block_size(lines, ROW_F)
        tx, ty = row.x + DOT + GAP, y + (row_h - th) / 2
        text.draw(cv, lines, ROW_F, tx, ty, _kit.INK, alpha=a)
        cv.mark(f'label-{word}', tx, ty, tw, th)


FILM = vb.Film(draw=draw, fps=FPS, frames=TOTAL, formats=(_kit.FORMAT,), background=_kit.BG,
               keyframes=((LAST_ENTER_START + ENTER + 4, 'all in'), (LEAVE_START - 4, 'held')))

if __name__ == '__main__':
    vb.main(__file__)
