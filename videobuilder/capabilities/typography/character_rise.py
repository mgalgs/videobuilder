"""Character Rise: the letters of a line come up one after another from under
a hidden edge at the line's foot, each sliding into place as if pushed up
through a slot."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def rise_offsets(text, p, stagger=0.6, ease=vb.ease_out_expo):
    """How far each character of `text` still has to rise at progress `p`
    (0 -> 1), as a fraction of the line height: 1 is fully hidden below the
    edge, 0 is at rest. Character `i` starts at `stagger * i / (len - 1)` and
    every character takes the remaining `1 - stagger` to arrive, shaped by
    `ease`. Spaces are 0 (there is nothing to see)."""
    n = len(text)
    span = 1 - stagger
    out = []
    for i, ch in enumerate(text):
        start = stagger * i / (n - 1) if n > 1 else 0.0
        k = vb.clamp01((p - start) / span) if span > 0 else float(p >= start)
        out.append(0.0 if ch.isspace() else 1 - ease(k))
    return out


def draw_character_rise(cv, text, font, x, y, p, color, stagger=0.6, ease=vb.ease_out_expo, alpha=1.0):
    """Draw `text` rising in at progress `p` from its top-left (x, y). The
    line's own box is the mask: each character starts one line height lower,
    out of sight below the box's bottom edge, and slides up to its place,
    left to right, `stagger` and `ease` as in `rise_offsets`. Returns the
    Box of the finished line."""
    w, h = vb.text.block_size([text], font)
    pad = h * 0.15  # room for accents above and tails below; the mask edge sits just under the descenders
    left = x
    with cv.clip(x - pad, y - pad, w + 2 * pad, h + 2 * pad):
        for ch, dy in zip(text, rise_offsets(text, p, stagger, ease)):
            adv = vb.text.measure(ch, font)
            if dy < 1 and not ch.isspace():
                vb.text.draw(cv, [ch], font, left, y + dy * (h + 2 * pad), color, alpha=alpha)
            left += adv
    return vb.Box(x, y, w, h)


def draw(n, cv):
    f = demo.font(120, 800)
    lines = (('Rising up,', demo.INK, 0.3, 1.5), ('one by one.', demo.ACCENT, 0.9, 2.2))
    h = vb.text.line_height(f)
    top = demo.H / 2 - h
    for i, (text, color, start, end) in enumerate(lines):
        w = vb.text.measure(text, f)
        box = draw_character_rise(cv, text, f, (demo.W - w) / 2, top + i * h * 1.05,
                                  demo.phase(n, start, end), color)
        cv.mark('text', *box)


CAPABILITY = Capability(
    id='character-rise',
    name='Character rise',
    family='typography',
    group='Per-unit reveals',
    aliases=('mask rise', 'line rise from mask', 'character stagger reveal', 'split text reveal'),
    definition='Letters push up one after another from behind an unseen line at the foot of the text, '
               'each sliding into its place until the whole word stands.',
    phrasings=('the letters slide up into view one at a time, like they come out of a slot',
               'staggered per-letter reveal where each character pops up from below a hidden edge',
               'make the title rise in character by character from under a line'),
    related=('text-mask-reveal', 'text-reveal-through-shape-mask', 'falling-glyph-rain-reveal',
             'long-shadow-growth', 'typewriter-reveal', 'drop-shadow-lift'),
    api=('videobuilder.capabilities.typography.character_rise.draw_character_rise',
         'videobuilder.capabilities.typography.character_rise.rise_offsets'),
    demo=lambda: demo.film(draw),
)
