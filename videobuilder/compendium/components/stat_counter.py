"""Data: stat counter. A hero number counts up from zero to its final value
on an eased ramp, with a label underneath -- the way a benchmark or a result
should land: with weight, not just appearing.

Ported and generalised from `examples/capabilities/counting-numbers.py`.
"""
import videobuilder as vb
from videobuilder import text

from .. import kit
from ..schema import Component, Slot

ENTER = 36


def draw(cv, shot):
    cv.fill(kit.BG)
    data = shot.data
    s = kit.safe(cv)
    number_f = kit.mono(96, 700)
    label_f = kit.font(22, 600)
    p = vb.interpolate(shot.f, [0, ENTER], [0, 1], ease=vb.ease_out_expo)
    shown = f'{data["value"] * p:.1f}{data["suffix"]}'
    number_lines = text.wrap(shown, number_f, s.w)
    nw, nh = text.block_size(number_lines, number_f)
    label_lines = text.wrap(data['label'], label_f, s.w)
    lw, lh = text.block_size(label_lines, label_f)
    total_h = nh + 16 + lh
    top = s.cy - total_h / 2
    text.draw(cv, number_lines, number_f, s.cx - nw / 2, top, kit.INK, align='center', width=nw)
    cv.mark('value', s.cx - nw / 2, top, nw, nh)
    text.draw(cv, label_lines, label_f, s.cx - lw / 2, top + nh + 16, kit.MUTED, align='center', width=lw)
    cv.mark('label', s.cx - lw / 2, top + nh + 16, lw, lh)


COMPONENT = Component(
    id='stat-counter',
    kind='data',
    description='A hero number that counts up from zero to its final value on an eased ramp, with a label underneath.',
    tags=('data', 'stat', 'number', 'hero'),
    formats=('16x9', '9x16', '1x1'),
    beats=(2, 5),
    slots=(
        Slot('value', 'number', True, 'The final value counted up to.'),
        Slot('label', 'text', True, 'What the number means, e.g. "faster than the baseline".', max_length=60),
        Slot('suffix', 'text', False, 'Unit shown right after the number, e.g. "x" or "%".', max_length=6),
    ),
    sample={'value': 2.4, 'label': 'faster than the baseline', 'suffix': 'x'},
    draw=draw,
)
