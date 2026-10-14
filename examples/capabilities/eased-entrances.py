"""Capability: eased entrances. The named motion tokens, side by side, each
sliding its chip in from the left on its own row so the curves can be
compared directly.

    python -m videobuilder preview examples/capabilities/eased-entrances.py

LOOP = True: each row enters, holds, then leaves exactly as it came, so the
last few frames and the first few frames are both "off screen, at rest".
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import text  # noqa: E402

LOOP = True
GRID = _kit.grid(bpm=120)      # 15 frames/beat
TIMELINE = vb.Timeline(GRID, [vb.Segment('loop', 0, 8)], end=8)   # 4.0 s

TOKENS = (
    ('ease_out_expo', vb.ease_out_expo, 'fast in, settles early'),
    ('ease_out_quint', vb.ease_out_quint, 'restrained entrance'),
    ('ease_in_out_quart', vb.ease_in_out_quart, 'travel across the screen'),
    ('ease_out_back', vb.ease_out_back, 'small overshoot'),
)

ENTER, HOLD, LEAVE = 14, 54, 14   # frames; 14+54+14 = 82 < 120 total frames

ROW_FONT = _kit.font(26, 650)
LABEL_FONT = _kit.font(17, 500)


def row_p(ease, n):
    """0 (not yet entered) .. 1 (in place) .. 0 (left again), eased both ways."""
    if n < ENTER:
        return vb.interpolate(n, [0, ENTER], [0, 1], ease=ease)
    if n < ENTER + HOLD:
        return 1.0
    leave_n = n - (ENTER + HOLD)
    if leave_n < LEAVE:
        return vb.interpolate(leave_n, [0, LEAVE], [1, 0], ease=vb.ease_in_expo)
    return 0.0


CHIP_W, CHIP_H = 150, 54
LABEL_W = 230


def draw(n, cv):
    cv.fill(_kit.BG)
    s = _kit.safe(cv, 64)
    title_f = _kit.font(32, 700)
    _kit.text_marked(cv, 'title', text.wrap('Eased entrances', title_f, s.w), title_f, s.x, s.y, _kit.INK)
    rows = s.pad(72, 0, 0, 0).stack([74] * len(TOKENS), gap=28)[0]
    lane_w = s.w - LABEL_W - 28 - CHIP_W   # the chip's travel, stopping short of the label column
    for row, (name, ease, note) in zip(rows, TOKENS):
        p = row_p(ease, n)
        if p > 0.02:
            x = row.x + p * lane_w
            _kit.rect_marked(cv, f'chip-{name}', x, row.y, CHIP_W, CHIP_H, _kit.ACCENT, radius=10, alpha=min(1, p * 3))
        token_h, note_h = text.block_size(text.wrap(name, ROW_FONT, LABEL_W), ROW_FONT)[1], \
            text.block_size(text.wrap(note, LABEL_FONT, LABEL_W), LABEL_FONT)[1]
        label_top = row.y + CHIP_H / 2 - (token_h + note_h) / 2
        _kit.text_marked(cv, f'token-{name}', text.wrap(name, ROW_FONT, LABEL_W), ROW_FONT,
                         row.right - LABEL_W, label_top, _kit.INK, align='right', width=LABEL_W)
        _kit.text_marked(cv, f'note-{name}', text.wrap(note, LABEL_FONT, LABEL_W), LABEL_FONT,
                         row.right - LABEL_W, label_top + token_h, _kit.MUTED, align='right', width=LABEL_W)


FILM = vb.Film(draw=draw, timeline=TIMELINE, formats=(_kit.FORMAT,), background=_kit.BG, keyframes=(ENTER + 5, ENTER + HOLD))

if __name__ == '__main__':
    vb.main(__file__)
