"""Transition: overlap slide. One card holds, then the next slides up over it
-- built on the timeline's own `Segment(overlap=...)`, the same mechanism an
ordinary film uses for a hard cut, not a crossfade (or a private timeline)
bolted on.

Ported and generalised from `examples/capabilities/overlap-transitions.py`.
Draws its own labelled from/to pair, the way that capability demo draws its
own cards A and B, but -- unlike the demo, which never has a "before" to
receive -- as the real outgoing and incoming shots of the film it sits in.
"""
import videobuilder as vb
from videobuilder import text

from .. import kit
from ..schema import Component, Slot


def _card(cv, box, letter_f, y, label, color, mark):
    cv.rect(box.x, y, box.w, box.h, kit.LINE, radius=20)
    cv.outline(box.x, y, box.w, box.h, color, width=4, radius=20)
    cv.mark(f'card-{mark}', box.x, y, box.w, box.h)
    lines = text.wrap(label, letter_f, box.w)
    _, lh = text.block_size(lines, letter_f)
    letter_box = text.draw(cv, lines, letter_f, box.x, y + (box.h - lh) / 2, kit.INK,
                           align='center', width=box.w)
    cv.mark(f'label-{mark}', *letter_box)


def draw(cv, shots):
    """`shots` is this frame's `Timeline.live(n)`: just the outgoing shot
    before the transition starts (holds at rest), or (outgoing, this
    transition's own shot) while it overlaps the one before it -- in a real
    film as much as in its own preview (see `catalog.component_film`)."""
    cv.fill(kit.BG)
    shot = shots[-1]
    data = shot.data
    box = kit.safe(cv, 72)
    letter_f = kit.font(96, 700)
    _card(cv, box, letter_f, box.y, data['from_label'], data['from_color'], 'from')
    if len(shots) == 1:
        return

    frames_per_beat = shot.length / (shot.segment.until - shot.segment.at)
    overlap_frames = max(1, round(frames_per_beat * shot.segment.overlap))
    p = vb.clamp01(vb.interpolate(shot.f, [0, overlap_frames], [0, 1], ease=vb.ease_in_out_quart))
    _card(cv, box, letter_f, box.y + box.h * (1 - p), data['to_label'], data['to_color'], 'to')


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
    overlap_ok=(('card-from', 'label-from'), ('card-to', 'label-to')),
)
