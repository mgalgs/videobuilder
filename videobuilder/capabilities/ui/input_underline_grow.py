"""Input underline grow: when a text field takes focus, a coloured bar grows
out from the middle of its bottom edge until it spans the whole field."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def draw_underline_grow(cv, x, y, w, p, color, rest=None, width=4, rest_width=2, origin=0.5,
                        ease=vb.ease_out_expo):
    """The focus underline of a field whose bottom edge runs from (x, y) to
    (x + w, y), at progress `p` (0 -> 1). A thin `rest` line (skipped if None)
    always spans the field; over it a `width`-px bar in `color` grows from the
    point `origin` of the way along (0.5: the centre) out to both ends, shaped
    by `ease`. Run `p` back from 1 to 0 for the blur. Returns the bar's Box."""
    if rest is not None:
        cv.rect(x, y - rest_width, w, rest_width, rest)
    q = ease(vb.clamp01(p))
    cx = x + w * origin
    x0, x1 = cx - (cx - x) * q, cx + (x + w - cx) * q
    if x1 > x0:
        cv.rect(x0, y - width, x1 - x0, width, color)
    return vb.Box(x0, y - width, x1 - x0, width)


FW, FH = 720, 128
LABEL, TEXT = 'Your name', 'MOTION'


def draw(n, cv):
    t = n / demo.FPS
    x, y = (demo.W - FW) / 2, (demo.H - FH) / 2 + 20
    p = demo.phase(n, 0.9, 1.9)
    label = demo.font(30, 600)
    vb.text.draw(cv, [LABEL], label, x + 4, y - 52, demo.TEAL if p > 0 else demo.MUTED)
    cv.rect(x, y, FW, FH, '#1d1f26', radius=14)
    f = demo.font(56, 800)
    tw, th = vb.text.block_size([TEXT], f)
    vb.text.draw(cv, [TEXT], f, x + 36, y + (FH - th) / 2, demo.INK)
    with cv.clip(x, y, FW, FH, radius=14):
        bar = draw_underline_grow(cv, x, y + FH, FW, p, demo.TEAL, rest=demo.LINE, width=6)
    cv.mark('field', x, y, FW, FH)
    cv.mark('underline', *bar)
    if p > 0 and int((t - 0.9) * 2.4) % 2 == 0:  # the caret blinks once focused
        cv.rect(x + 36 + tw + 14, y + 30, 4, FH - 60, demo.TEAL)
    k = demo.phase(n, 0.8, 1.3)  # the click that focuses the field
    if 0 < k < 1:
        cx, cy = x + FW * 0.62, y + FH * 0.62
        cv.arc(cx, cy, 14 + 40 * k, 0, 2 * math.pi, demo.INK, width=3, alpha=1 - k)
        demo.dot(cv, cx, cy, r=10, color=demo.INK, alpha=1 - k)


CAPABILITY = Capability(
    id='input-underline-grow',
    name='Input underline grow',
    family='ui',
    group='Forms',
    aliases=('focus underline', 'input bar expand'),
    definition='A text field gains focus and an accent bar spreads out from the middle of its bottom edge '
               'to both ends, marking it active.',
    phrasings=('clicking the text box makes a coloured line stretch out along the bottom',
               'the field gets an underline that expands from the centre when you tap it',
               'a focus line that grows across the input from the middle'),
    related=('underline-wipe', 'tab-underline-slide', 'character-blur-in', 'underline-swash-draw',
             'border-glow-follow', 'focus-blur-out'),
    api=('videobuilder.capabilities.ui.input_underline_grow.draw_underline_grow',),
    demo=lambda: demo.film(draw),
)
