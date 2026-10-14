"""Capability: bar charts. A small bar chart grows each bar on its own beat,
with the value labelled directly at the end of the bar -- no legend. The
hero bar (the last one to land) is told apart by colour and by a different
fill structure, not colour alone.

    python -m videobuilder preview examples/capabilities/bar-charts.py

LOOP = True: the bars grow in beat by beat, hold, then shrink back to zero in
reverse beat order -- exactly as they came in, run backwards -- resting on
an empty chart (title and baseline only) at both ends.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import Box, fr, text  # noqa: E402

LOOP = True
GRID = _kit.grid(bpm=200)   # 9 frames/beat: a brisk cascade across 4 beats

BARS = (
    ('Baseline', 1.0, False),
    ('Cache', 1.6, False),
    ('Batch', 2.1, False),
    ('Pipeline', 3.2, True),   # hero: grows last, lands on its own beat
)
AXIS_MAX = 3.6

GROW = vb.damped(0.65, hz=2.5)         # a small pop as each bar lands
SHRINK_STAGGER = 9                     # frames; mirrors the beat spacing
EXIT_LEN = 16
HOLD_END = 65
SHRINK_START = HOLD_END
TOTAL = 116                            # ~3.9 s

TITLE = 'Stage throughput'
TITLE_F = _kit.font(32, 700)
NAME_F = _kit.font(20, 600)
VALUE_F = _kit.font(26, 700, family=_kit.MONO)

BAR_W = 64


def bar_p(i, n):
    """0 (not grown) -> ~1, with a little pop -> back to 0, mirrored in
    reverse order for the exit."""
    beat_start = GRID.b(i)
    grow = max(0.0, vb.spring_at(n - beat_start, GRID.fps, **GROW))
    if n < SHRINK_START:
        return grow
    delay = (len(BARS) - 1 - i) * SHRINK_STAGGER
    local = n - SHRINK_START - delay
    if local <= 0:
        return grow
    shrink = vb.interpolate(local, [0, EXIT_LEN], [1, 0], ease=vb.ease_in_expo)
    return grow * shrink


def draw(n, cv):
    cv.fill(_kit.BG)
    s = _kit.safe(cv, 64)
    _kit.text_marked(cv, 'title', text.wrap(TITLE, TITLE_F, s.w), TITLE_F, s.x, s.y, _kit.INK)

    name_h = text.line_height(NAME_F) + 12
    plot_top = s.y + 96
    baseline_y = s.bottom - name_h
    plot = Box(s.x, plot_top, s.w, baseline_y - plot_top)
    cols = plot.row(fr, fr, fr, fr, gap=36)

    cv.line(s.x, baseline_y, s.right, baseline_y, _kit.LINE, width=2)

    for i, (col, (name, value, hero)) in enumerate(zip(cols, BARS)):
        _kit.text_marked(cv, f'name-{name}', [name], NAME_F, col.x, baseline_y + 10, _kit.MUTED,
                          align='center', width=col.w)
        p = bar_p(i, n)
        if p <= 0.02:
            continue
        h = min(plot.h, value * p / AXIS_MAX * plot.h)
        y = baseline_y - h
        fill = _kit.ACCENT if hero else _kit.LINE
        cv.rect(col.cx - BAR_W / 2, y, BAR_W, h, fill, radius=8)
        if not hero:
            cv.outline(col.cx - BAR_W / 2, y, BAR_W, h, _kit.MUTED, width=2, radius=8)
        cv.mark(f'bar-{name}', col.cx - BAR_W / 2, y, BAR_W, h)
        shown = f'{value * min(1.0, p):.1f}x'
        vw, vh = text.block_size([shown], VALUE_F)
        label_y = max(plot.y, y - vh - 8)
        _kit.text_marked(cv, f'value-{name}', [shown], VALUE_F, col.cx - vw / 2, label_y, _kit.INK)


FILM = vb.Film(draw=draw, fps=GRID.fps, frames=TOTAL, formats=(_kit.FORMAT,), background=_kit.BG,
               keyframes=((24, 'cascading'), (60, 'all grown')))

if __name__ == '__main__':
    vb.main(__file__)
