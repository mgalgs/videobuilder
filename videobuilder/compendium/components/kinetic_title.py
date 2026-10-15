"""Title: kinetic title. A short headline wraps with balanced line breaks and
reveals word by word, each word's variable-font weight animating in as it
lands -- thin to bold, not just appearing. The last word lands in the accent
colour.

Ported and generalised from `examples/capabilities/kinetic-typography.py`.
"""
import videobuilder as vb
from videobuilder import text

from .. import kit
from ..schema import Component, Slot

SIZE = 54
START_WEIGHT, FINAL_WEIGHT = 380, 760
WEIGHT_SPAN = 18
RISE = vb.damped(0.75, hz=4.0)
STAGGER = 3


def draw(cv, shot):
    cv.fill(kit.BG)
    data = shot.data
    s = kit.safe(cv)
    f = kit.font(SIZE, FINAL_WEIGHT)
    lines = text.wrap(data['headline'], f, s.w, balance=True)
    lh = text.line_height(f)
    _, block_h = text.block_size(lines, f)
    top = s.cy - block_h / 2
    space_w = text.measure(' ', f)
    words = []
    delay = 0
    for i, line in enumerate(lines):
        line_w = text.measure(line, f)
        x = s.cx - line_w / 2
        y = top + i * lh
        for w in line.split(' '):
            words.append((w, x, y, delay))
            x += text.measure(w, f) + space_w
            delay += STAGGER
    n_words = len(words)
    for i, (word, x, y, delay) in enumerate(words):
        local_f = shot.f - delay
        rise = vb.clamp01(vb.spring_at(local_f, 30, **RISE))
        if rise <= 0.01:
            continue
        weight = round(vb.interpolate(local_f, [0, WEIGHT_SPAN], [START_WEIGHT, FINAL_WEIGHT], ease=vb.ease_out_quint))
        wf = kit.font(SIZE, weight)
        dy = (1 - rise) * 14
        color = data['accent'] if i == n_words - 1 else kit.INK
        box = text.draw(cv, [word], wf, x, y + dy, color, alpha=rise)
        cv.mark(f'word-{i}', *box)


COMPONENT = Component(
    id='kinetic-title',
    kind='title',
    description='A short headline that reveals word by word, each word animating thin to bold as it lands.',
    tags=('title', 'headline', 'type', 'reveal'),
    formats=('16x9', '9x16', '1x1'),
    beats=(2, 5),
    slots=(
        Slot('headline', 'text', True, 'The headline, a few words; wraps and reveals word by word.', max_length=40),
        Slot('accent', 'color', False, "Colour of the last word, so the line ends on an accent."),
    ),
    sample={'headline': 'Words land with weight', 'accent': kit.ACCENT},
    draw=draw,
)
