"""Per-line Fade-in: a paragraph appears one line at a time, each line fading
up in place once the line above it is fully there."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _smooth(x):
    return x * x * (3 - 2 * x)


def line_alphas(count, p, overlap=0.0):
    """Opacity 0 -> 1 of each of `count` lines at progress `p` (0 -> 1). The
    reveal is split into equal slots, one line per slot in order; `overlap`
    (0 -> 1) lets each line start that fraction of a slot before the one above
    has finished (0: strictly one after another)."""
    if count <= 0:
        return []
    slot = 1 / (count - (count - 1) * overlap)
    step = slot * (1 - overlap)
    return [_smooth(vb.clamp01((p - i * step) / slot)) for i in range(count)]


def draw_line_fade(cv, lines, font, x, y, p, color, align='left', width=None, overlap=0.0):
    """Draw `lines` top-down from (x, y) fading in one by one at progress `p`,
    laid out exactly as `vb.text.draw` would set the finished block, so no
    line shifts as the others arrive. `align` within `width` (default: the
    block's). `overlap` goes to `line_alphas`. Returns the finished block's Box."""
    lines = [lines] if isinstance(lines, str) else list(lines)
    bw, bh = vb.text.block_size(lines, font)
    width = bw if width is None else width
    lh = vb.text.line_height(font)
    for i, (line, a) in enumerate(zip(lines, line_alphas(len(lines), p, overlap))):
        if a > 0:
            vb.text.draw(cv, [line], font, x, y + i * lh, color, align=align, width=width, alpha=a)
    return vb.Box(x, y, width, bh)


LINES = ('A quiet room at dawn.', 'The kettle starts to sing.', 'Somewhere, a door opens.')


def draw(n, cv):
    f = demo.font(72, 700)
    w, h = vb.text.block_size(LINES, f)
    box = draw_line_fade(cv, LINES, f, (demo.W - w) / 2, (demo.H - h) / 2, demo.phase(n, 0.3, 2.5), demo.INK)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='per-line-fade-in',
    name='Per-line fade-in',
    family='typography',
    group='Per-unit reveals',
    aliases=('line-by-line reveal', 'line-by-line fade', 'staggered line fade'),
    definition='A block of text appears one line at a time, each line fading up in its place '
               'after the line above it has fully arrived.',
    phrasings=('have the paragraph fade in a line at a time',
               'reveal the text one row after another, each gently fading on',
               'bring the lines of the quote up in sequence instead of all at once'),
    related=('fade-up-scroll-reveal', 'lyric-line-crossfade', 'player-movement-trail',
             'scroll-driven-text-reveal', 'tooltip-fade-follow', 'terminal-line-print'),
    api=('videobuilder.capabilities.typography.per_line_fade_in.draw_line_fade',
         'videobuilder.capabilities.typography.per_line_fade_in.line_alphas'),
    demo=lambda: demo.film(draw),
)
