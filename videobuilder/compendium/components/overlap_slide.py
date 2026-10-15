"""Transition: overlap slide. One card holds, then the next slides up over it
-- a transition built from `Timeline`/`Segment(overlap=...)`, the same
mechanism an ordinary film uses for a hard cut, not a crossfade bolted on.

Ported and generalised from `examples/capabilities/overlap-transitions.py`.
Draws its own from/to pair (there is no neighbouring shot to receive), the
way that capability demo draws its own cards A and B.
"""
import videobuilder as vb
from videobuilder import text

from .. import kit
from ..schema import Component, Slot


def _inner_timeline(length):
    """A private two-segment Timeline sized to exactly `length` frames: `from`
    holds, `to` starts partway through and overlaps the last third of `from`.
    A `Grid` with one frame per beat lets beats double as frame counts."""
    grid = vb.Grid(fps=30, bpm=30 * 60)
    to_len = max(2, round(length * 0.55))
    overlap = max(1, min(to_len - 1, round(length * 0.22)))
    from_until = length - to_len + overlap
    segments = [
        vb.Segment('from', 0, from_until),
        vb.Segment('to', from_until, length, overlap=overlap),
    ]
    return vb.Timeline(grid, segments, end=length)


def draw(cv, shot):
    cv.fill(kit.BG)
    data = shot.data
    tl = _inner_timeline(shot.length)
    box = kit.safe(cv, 72)
    letter_f = kit.font(96, 700)
    for inner in tl.live(min(shot.f, shot.length - 1)):
        is_from = inner.name == 'from'
        label = data['from_label'] if is_from else data['to_label']
        color = data['from_color'] if is_from else data['to_color']
        if inner.exit is not None:
            y = box.y  # the outgoing card holds still while covered
        elif inner.segment.overlap:
            p = vb.clamp01(inner.f / max(1, tl.grid.b(inner.segment.overlap)))
            y = box.y + box.h * (1 - vb.ease_in_out_quart(p))
        else:
            y = box.y
        cv.rect(box.x, y, box.w, box.h, kit.LINE, radius=20)
        cv.outline(box.x, y, box.w, box.h, color, width=4, radius=20)
        cv.mark(f'card-{inner.name}', box.x, y, box.w, box.h)
        lines = text.wrap(label, letter_f, box.w)
        _, lh = text.block_size(lines, letter_f)
        letter_box = text.draw(cv, lines, letter_f, box.x, y + (box.h - lh) / 2, kit.INK,
                               align='center', width=box.w)
        cv.mark(f'label-{inner.name}', *letter_box)


COMPONENT = Component(
    id='overlap-slide',
    kind='transition',
    description='One card holds, then the next slides up over it, built on the timeline\'s own overlap, not a crossfade.',
    tags=('transition', 'slide', 'cut'),
    formats=('16x9', '9x16', '1x1'),
    beats=(2, 4),
    slots=(
        Slot('from_label', 'text', True, 'Short label on the outgoing card.', max_length=16),
        Slot('to_label', 'text', True, 'Short label on the incoming card.', max_length=16),
        Slot('from_color', 'color', False, 'Outline colour of the outgoing card.'),
        Slot('to_color', 'color', False, 'Outline colour of the incoming card.'),
    ),
    sample={'from_label': 'Before', 'to_label': 'After', 'from_color': kit.ACCENT, 'to_color': kit.TEAL},
    draw=draw,
)
