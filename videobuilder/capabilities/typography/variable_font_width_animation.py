"""Variable-font width animation: a word's letters widen and narrow along a
width axis, condensed to extended, at a fixed height, the line re-spacing as
they go. None of the fonts videobuilder ships has a width axis, so this draws
one: each glyph is scaled across, and on a variable-weight font its weight
moves the other way so the upright strokes keep about the same thickness."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def stroke_weight(weight, width):
    """The weight that keeps upright strokes about as thick as `weight` once a
    glyph is scaled across by `width`, clamped to the 100-900 axis."""
    return max(100, min(900, weight / width))


def width_wave(n_letters, p, lo=0.6, hi=1.5, stagger=0.5, ease=vb.ease_in_out_quart):
    """Per-letter widths at progress `p` (0 -> 1) of a move from `lo` to `hi`:
    the first letter leads, the last starts `stagger` of the way in, each
    eased by `ease`. Swap `lo` and `hi` to narrow instead."""
    span = 1 - stagger
    out = []
    for i in range(n_letters):
        start = stagger * i / max(1, n_letters - 1)
        out.append(lo + (hi - lo) * ease(vb.clamp01((p - start) / span)))
    return out


def draw_width(cv, text, font, cx, cy, width, color, keep_stroke=True, alpha=1.0):
    """Draw `text` on one line centred at (cx, cy) with every glyph `width`
    times its normal width (1 = as designed, under 1 condensed, over 1
    extended); `width` may be one number or one per character. The height
    never changes, only the widths and so the spacing. `keep_stroke` trades
    weight against width (see `stroke_weight`). Returns the line's Box."""
    widths = [width] * len(text) if isinstance(width, (int, float)) else list(width)
    if len(widths) != len(text):
        raise ValueError(f'draw_width: {len(widths)} widths for {len(text)} characters')
    fonts = [vb.Font(font.family, font.size, weight=stroke_weight(font.weight, w) if keep_stroke else font.weight,
                     style=font.style) for w in widths]
    advances = [vb.text.measure(ch, f) * w for ch, f, w in zip(text, fonts, widths)]
    total = sum(advances) + font.tracking * font.size * max(0, len(text) - 1)
    h = vb.text.line_height(font)
    x, top = cx - total / 2, cy - h / 2
    ctx = cv.ctx
    for ch, f, w, adv in zip(text, fonts, widths, advances):
        if not ch.isspace():
            ctx.save()
            ctx.translate(x, top)
            ctx.scale(w, 1)
            vb.text.draw(cv, [ch], f, 0, 0, color, alpha=alpha)
            ctx.restore()
        x += adv + font.tracking * font.size
    return vb.Box(cx - total / 2, top, total, h)


LO, HI = 0.55, 1.55


def _slider(cv, v, y):
    """A small width-axis readout: a track from condensed to extended, a
    handle at `v` and the axis value under it."""
    x0, x1 = demo.W / 2 - 200, demo.W / 2 + 200
    cv.line(x0, y, x1, y, demo.LINE, width=4)
    t = (v - LO) / (HI - LO)
    cv.line(x0, y, x0 + (x1 - x0) * t, y, demo.TEAL, width=4)
    demo.dot(cv, x0 + (x1 - x0) * t, y, r=9, color=demo.TEAL)
    f = demo.mono(18, 500)
    vb.text.draw(cv, ['condensed'], f, x0, y + 18, demo.MUTED)
    vb.text.draw(cv, ['extended'], f, x1 - vb.text.measure('extended', f), y + 18, demo.MUTED)
    label = f'wdth {round(100 * v)}'
    vb.text.draw(cv, [label], f, demo.W / 2 - vb.text.measure(label, f) / 2, y + 18, demo.INK)


def draw(n, cv):
    text = 'STRETCH'
    out = width_wave(len(text), demo.phase(n, 0.3, 1.5), LO, HI)        # condensed -> extended
    back = demo.phase(n, 1.8, 2.8)
    widths = width_wave(len(text), back, HI, 1.0) if back > 0 else out  # settles at the designed width
    box = draw_width(cv, text, demo.font(120, 600), demo.W / 2, demo.H / 2 - 30, widths, demo.INK)
    cv.mark('text', *box)
    _slider(cv, sum(widths) / len(widths), demo.H / 2 + 110)


CAPABILITY = Capability(
    id='variable-font-width-animation',
    name='Variable-font width animation',
    family='typography',
    group='Variable font',
    aliases=('width axis animation', 'wdth animation', 'condensed to extended', 'font stretch animation'),
    definition='The letters of a word grow wider or narrower at the same height, sweeping from condensed '
               'to extended type while the line re-spaces around them.',
    phrasings=('make the title stretch out wide and then squeeze back',
               'animate the font from narrow to wide letter by letter',
               'the word breathes in and out horizontally like a variable font'),
    related=('text-to-shape-morph', 'chart-type-morph', 'axis-rescale', 'twirl-warp-text', 'julia-set-morph',
             'arc-bend-morph'),
    api=('videobuilder.capabilities.typography.variable_font_width_animation.draw_width',
         'videobuilder.capabilities.typography.variable_font_width_animation.width_wave',
         'videobuilder.capabilities.typography.variable_font_width_animation.stroke_weight'),
    demo=lambda: demo.film(draw),
)
