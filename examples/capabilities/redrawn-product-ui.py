"""Capability: redrawn product UI. A small settings panel built from three
measured blocks (header, toggle row, button) and stacked with `Box.stack`,
drawn as crisp vector shapes and real text instead of a captured bitmap.

    python -m videobuilder preview examples/capabilities/redrawn-product-ui.py

LOOP = True: the panel springs into place as a card, holds, then eases back
out the way it came, so both ends of the clip are the same "not yet
arrived" rest state (the panel fully below frame).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import Box, text  # noqa: E402

LOOP = True
FPS = 30
TOTAL = 90          # 3.0 s
LEAVE_START, LEAVE = 64, 18
SPRING = vb.damped(0.55, hz=2.0)

ICON, GAP = 40, 16
SWITCH_W, SWITCH_H = 56, 30
BTN_H = 56
PANEL_W, PAD, BLOCK_GAP = 480, 28, 20
RISE, SCALE0 = 560, 0.86   # entrance travel and starting scale


class Header:
    def __init__(self, title):
        self.title, self.font = title, _kit.font(26, 700)

    def height(self, w):
        lines = text.wrap(self.title, self.font, w - ICON - GAP)
        return max(ICON, text.block_size(lines, self.font)[1])

    def draw(self, cv, box, name):
        icon_y = box.y + (box.h - ICON) / 2
        _kit.rect_marked(cv, f'{name}-icon', box.x, icon_y, ICON, ICON, _kit.ACCENT, radius=10)
        cv.rect(box.x + ICON * 0.60, icon_y + ICON * 0.22, ICON * 0.18, ICON * 0.18, _kit.INK, radius=ICON * 0.09)
        lines = text.wrap(self.title, self.font, box.w - ICON - GAP)
        th = text.block_size(lines, self.font)[1]
        _kit.text_marked(cv, f'{name}-title', lines, self.font, box.x + ICON + GAP, box.y + (box.h - th) / 2, _kit.INK)


class ToggleRow:
    def __init__(self, label, sub):
        self.label, self.sub = label, sub
        self.label_f, self.sub_f = _kit.font(21, 600), _kit.font(16, 450)

    def _text_h(self, w):
        tw = w - SWITCH_W - GAP
        label_lines = text.wrap(self.label, self.label_f, tw)
        sub_lines = text.wrap(self.sub, self.sub_f, tw)
        lh = text.block_size(label_lines, self.label_f)[1]
        sh = text.block_size(sub_lines, self.sub_f)[1]
        return label_lines, sub_lines, lh, sh

    def height(self, w):
        _, _, lh, sh = self._text_h(w)
        return max(SWITCH_H, lh + 6 + sh)

    def draw(self, cv, box, name):
        label_lines, sub_lines, lh, sh = self._text_h(box.w)
        top = box.y + (box.h - (lh + 6 + sh)) / 2
        text_w = box.w - SWITCH_W - GAP
        _kit.text_marked(cv, f'{name}-label', label_lines, self.label_f, box.x, top, _kit.INK, width=text_w)
        _kit.text_marked(cv, f'{name}-sub', sub_lines, self.sub_f, box.x, top + lh + 6, _kit.MUTED, width=text_w)
        sw_x, sw_y = box.right - SWITCH_W, box.y + (box.h - SWITCH_H) / 2
        _kit.rect_marked(cv, f'{name}-switch', sw_x, sw_y, SWITCH_W, SWITCH_H, _kit.ACCENT, radius=SWITCH_H / 2)
        r = SWITCH_H / 2 - 4
        cv.rect(sw_x + SWITCH_W - 4 - 2 * r, sw_y + 4, 2 * r, 2 * r, _kit.INK, radius=r)


class Button:
    def __init__(self, label):
        self.label, self.font = label, _kit.font(21, 700)

    def height(self, w):
        return BTN_H

    def draw(self, cv, box, name):
        _kit.rect_marked(cv, name, box.x, box.y, box.w, box.h, _kit.INK, radius=14)
        lines = text.wrap(self.label, self.font, box.w)
        bw, bh = text.block_size(lines, self.font)
        text.draw(cv, lines, self.font, box.x + (box.w - bw) / 2, box.y + (box.h - bh) / 2, _kit.BG,
                  align='center', width=box.w)


BLOCKS = (
    ('header', Header('Notifications')),
    ('toggle', ToggleRow('Email alerts', 'Get notified about replies and mentions')),
    ('button', Button('Save changes')),
)

TITLE_F = _kit.font(32, 700)


def panel_p(n):
    """0 (below frame, not yet arrived) .. ~1 (settled) .. 0 (left again)."""
    if n < LEAVE_START:
        return vb.spring_at(n, FPS, **SPRING)
    lp = min(1.0, (n - LEAVE_START) / LEAVE)
    return 1 - vb.ease_in_expo(lp)


def draw(n, cv):
    cv.fill(_kit.BG)
    s = _kit.safe(cv, 64)
    title_box = _kit.text_marked(cv, 'title', text.wrap('Redrawn product UI', TITLE_F, s.w), TITLE_F,
                                  s.x, s.y, _kit.INK)

    content = Box(s.x, title_box.bottom + 28, s.w, s.bottom - title_box.bottom - 28)
    content_w = PANEL_W - 2 * PAD
    heights = [block.height(content_w) for _, block in BLOCKS]
    _, blocks_h = Box(0, 0, content_w, 0).stack(heights, gap=BLOCK_GAP)
    panel_h = blocks_h + 2 * PAD
    panel_box = Box(content.x + (content.w - PANEL_W) / 2, content.y + (content.h - panel_h) / 2, PANEL_W, panel_h)

    p = panel_p(n)
    scale = SCALE0 + (1 - SCALE0) * p
    ax, ay = panel_box.cx, panel_box.cy
    dx = ax * (1 - scale)
    dy = ay * (1 - scale) + (1 - p) * RISE

    with cv.layer(dx=dx, dy=dy, scale=scale):
        cv.shadow(*panel_box, radius=20, dy=18, blur=36, color=(0, 0, 0, 0.45))
        cv.rect(*panel_box, _kit.LINE, radius=20)
        inner = panel_box.pad(PAD)
        boxes, _ = inner.stack(heights, gap=BLOCK_GAP)
        for (name, block), box in zip(BLOCKS, boxes):
            block.draw(cv, box, name)


FILM = vb.Film(draw=draw, fps=FPS, frames=TOTAL, formats=(_kit.FORMAT,), background=_kit.BG,
               keyframes=((46, 'settled'), (60, 'hold')))

if __name__ == '__main__':
    vb.main(__file__)
