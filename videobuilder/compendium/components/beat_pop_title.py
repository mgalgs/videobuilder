"""Title: beat-pop title. A headline slams in on a spring, a subtitle settles
under it, and a ring of accent light pulses outward every beat -- the
grid-locked punctuation a title card gets on a cut.

Ported and generalised from the title hit in `examples/showcase_scenes/kit.py`
(`title`) and `examples/capabilities/pop-on-the-beat.py`.
"""
import math

import videobuilder as vb
from videobuilder import text

from .. import kit
from ..schema import Component, Slot

HEAD_SIZE = 64
SUB_SIZE = 28
FPB = 20  # frames a beat, at this component's own pace
BOUNCY = vb.damped(0.45, hz=2.4)


def draw(cv, shot):
    cv.fill(kit.BG)
    data = shot.data
    s = kit.safe(cv)
    accent = data['accent']
    head_f = kit.font(HEAD_SIZE, 800, tracking=-0.02)
    head_lines = text.wrap(data['headline'], head_f, s.w, balance=True)
    head_w, head_h = text.block_size(head_lines, head_f)
    has_sub = bool(data.get('subtitle'))
    sub_f = kit.font(SUB_SIZE, 500)
    sub_lines = text.wrap(data['subtitle'], sub_f, s.w, balance=True) if has_sub else ()
    sub_w, sub_h = text.block_size(sub_lines, sub_f) if has_sub else (0, 0)
    gap = 20 if has_sub else 0
    block_h = head_h + (gap + sub_h if has_sub else 0)
    top = s.cy - block_h / 2

    beat = shot.f // FPB
    for k in range(1, beat + 1):
        age = shot.f - k * FPB
        if 0 <= age < 24:
            cv.arc(s.cx, top + head_h / 2, head_w * 0.4 + age * 6, 0, 2 * math.pi, accent, width=3,
                   alpha=0.5 * (1 - age / 24))

    p = vb.spring_at(shot.f, 30, **BOUNCY)
    scale = max(0.0, p)
    if scale > 0.001:
        with cv.layer(dx=s.cx * (1 - scale), dy=(top + head_h / 2) * (1 - scale), scale=scale):
            box = text.draw(cv, head_lines, head_f, s.cx - head_w / 2, top, kit.INK, align='center', width=head_w)
        cv.mark('headline', s.cx - head_w / 2, top, head_w, head_h)
    if has_sub:
        q = vb.clamp01(vb.spring_at(shot.f - 10, 30, **BOUNCY))
        with cv.layer(opacity=q, dy=(1 - q) * 16):
            text.draw(cv, sub_lines, sub_f, s.cx - sub_w / 2, top + head_h + gap, kit.MUTED,
                      align='center', width=sub_w)
        cv.mark('subtitle', s.cx - sub_w / 2, top + head_h + gap, sub_w, sub_h)


COMPONENT = Component(
    id='beat-pop-title',
    kind='title',
    description='A headline that slams in on a spring with an accent ring pulsing on every beat, a subtitle settling under it.',
    tags=('title', 'headline', 'beat', 'hero'),
    formats=('16x9', '9x16', '1x1'),
    beats=(3, 6),
    slots=(
        Slot('headline', 'text', True, 'The hero headline, short -- a title card or a section break.', max_length=30),
        Slot('subtitle', 'text', False, 'One supporting line under the headline.', max_length=60),
        Slot('accent', 'color', False, 'Colour of the pulsing ring.'),
    ),
    sample={'headline': 'Launch day', 'subtitle': 'Everything, on time.', 'accent': kit.ACCENT},
    draw=draw,
)
