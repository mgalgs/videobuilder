"""Capability: one scene, laid out per format. Three miniature "device"
panels -- 9:16, 16:9, 1:1, the framework's three built-in sizes -- each
showing where a title band and a content block sit in THAT format's own
full-size geometry, fetched through the real `per_format` mechanism and
scaled down to fit inside a single panel.

    python -m videobuilder preview examples/capabilities/every-format.py

LOOP = True: the three panels enter one after another, hold together, then
leave the same way, so the last few frames and the first few frames are
both "not yet entered".
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import Box, per_format, text  # noqa: E402

LOOP = True
GRID = _kit.grid(bpm=120)      # 15 frames/beat
TIMELINE = vb.Timeline(GRID, [vb.Segment('loop', 0, 8)], end=8)   # 4.0 s

STAGGER = 6                        # frames between one panel's start and the next's (200 ms)
ENTER, HOLD, LEAVE = 14, 56, 14
N_PANELS = 3
LAST_ENTER_END = (N_PANELS - 1) * STAGGER + ENTER   # 26
LEAVE_START = LAST_ENTER_END + HOLD                  # 82
LAST_LEAVE_END = LEAVE_START + (N_PANELS - 1) * STAGGER + LEAVE   # 108, < 120 total frames
assert LAST_LEAVE_END + 6 <= 120, 'tail rest before the loop seam is too tight'

FORMATS3 = (
    vb.Format('9x16', 1080, 1920),
    vb.Format('16x9', 1920, 1080),
    vb.Format('1x1', 1080, 1080),
)


def _layout(fmt):
    """Where the title band and content block sit, in `fmt`'s own full-size
    coordinate space -- a real per-format layout, not three cosmetic copies."""
    s = Box(0, 0, fmt.width, fmt.height).pad(round(fmt.width * 0.08))
    if fmt.portrait:        # 9x16: a title band across the top, content fills below
        title_h = s.h * 0.14
        gap = s.h * 0.04
        return dict(title=Box(s.x, s.y, s.w, title_h),
                    content=Box(s.x, s.y + title_h + gap, s.w, s.h - title_h - gap))
    if fmt.landscape:        # 16x9: a title column on the left, content fills the right
        title_w = s.w * 0.28
        gap = s.w * 0.04
        return dict(title=Box(s.x, s.y, title_w, s.h),
                    content=Box(s.x + title_w + gap, s.y, s.w - title_w - gap, s.h))
    title_h = s.h * 0.18     # 1x1: a shallower title band, square content below
    gap = s.h * 0.05
    return dict(title=Box(s.x, s.y, s.w, title_h),
                content=Box(s.x, s.y + title_h + gap, s.w, s.h - title_h - gap))


LAYOUTS = {f.name: _layout(f) for f in FORMATS3}

TITLE_F = _kit.font(32, 700)
LABEL_F = _kit.font(20, 650)

SCALE = 0.12   # miniature px per format px, shared by all three panels
GAP = 48
RISE = 36


def panel_p(i, n):
    """0 (not yet entered) .. 1 (in place) .. 0 (left again), eased both ways,
    for panel i, staggered STAGGER frames after panel i - 1."""
    enter_n = n - i * STAGGER
    if enter_n < 0:
        return 0.0
    if enter_n < ENTER:
        return vb.interpolate(enter_n, [0, ENTER], [0, 1], ease=vb.ease_out_expo)
    if n < LEAVE_START:
        return 1.0
    leave_n = n - (LEAVE_START + i * STAGGER)
    if leave_n < 0:
        return 1.0
    if leave_n < LEAVE:
        return vb.interpolate(leave_n, [0, LEAVE], [1, 0], ease=vb.ease_in_expo)
    return 0.0


def draw(n, cv):
    cv.fill(_kit.BG)
    s = _kit.safe(cv, 64)
    _kit.text_marked(cv, 'title', text.wrap('Every format', TITLE_F, s.w), TITLE_F, s.x, s.y, _kit.INK)

    panel_ws = [f.width * SCALE for f in FORMATS3]
    panel_hs = [f.height * SCALE for f in FORMATS3]
    row_h = max(panel_hs)
    row_w = sum(panel_ws) + GAP * (len(FORMATS3) - 1)
    row_top = s.y + 120
    label_gap = 20

    xs = []
    x = s.cx - row_w / 2
    for pw in panel_ws:
        xs.append(x)
        x += pw + GAP

    for i, (f, pw, ph, x) in enumerate(zip(FORMATS3, panel_ws, panel_hs, xs)):
        a = panel_p(i, n)
        if a <= 0.015:
            continue
        alpha = min(1.0, a * 2.5)
        dy = (1 - a) * RISE
        with cv.layer(opacity=alpha, dy=dy):
            L = per_format(LAYOUTS, f)
            py = row_top + (row_h - ph)   # bottom-align panels of different heights
            cv.outline(x, py, pw, ph, _kit.LINE, width=2, radius=4)

            t = L['title']
            tx, ty, tw, th = x + t.x * SCALE, py + t.y * SCALE, t.w * SCALE, t.h * SCALE
            cv.rect(tx, ty, tw, th, _kit.ACCENT, radius=2)
            cv.mark(f'title-{f.name}', tx, ty, tw, th)

            c = L['content']
            ccx, ccy, cw, ch = x + c.x * SCALE, py + c.y * SCALE, c.w * SCALE, c.h * SCALE
            cv.rect(ccx, ccy, cw, ch, _kit.TEAL, radius=2, alpha=0.55)
            cv.mark(f'content-{f.name}', ccx, ccy, cw, ch)

            label = f.name.replace('x', ':')
            label_lines = text.wrap(label, LABEL_F, pw + 40)
            lw, lh = text.block_size(label_lines, LABEL_F)
            text.draw(cv, label_lines, LABEL_F, x + pw / 2 - lw / 2, row_top + row_h + label_gap,
                      _kit.MUTED, align='center', width=pw + 40)
            cv.mark(f'label-{f.name}', x + pw / 2 - lw / 2, row_top + row_h + label_gap, lw, lh)

            x += pw + GAP


FILM = vb.Film(draw=draw, timeline=TIMELINE, formats=(_kit.FORMAT,), background=_kit.BG,
               keyframes=(LAST_ENTER_END + 6, LEAVE_START))

if __name__ == '__main__':
    vb.main(__file__)
