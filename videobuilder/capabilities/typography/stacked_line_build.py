"""Stacked line build: lines of type land one at a time on top of each other,
the stack growing upward into a tight block while it stays centred."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def stack_arrivals(count, p, overlap=1.6, ease=vb.ease_out_quint):
    """Each of `count` lines' landing progress (0 -> 1) at overall progress
    `p`, in landing order: the first lands first, the last ends at `p = 1`.
    Every landing lasts `overlap / count` of the build, so neighbours overlap
    a little when `overlap > 1`."""
    if count <= 0:
        return []
    d = min(1.0, overlap / count)
    starts = [0.0] * count if count == 1 else [k * (1 - d) / (count - 1) for k in range(count)]
    return [ease(vb.clamp01((p - s) / d)) for s in starts]


def draw_stacked_lines(cv, lines, font, cx, cy, p, color, colors=None, leading=0.9, drop=None,
                       align='center', **kw):
    """Draw `lines` (top to bottom) building as a stack at progress `p`: the
    bottom line lands first and each line above drops onto the one beneath
    it, fading in. The block stays centred on (cx, cy) as it grows. Lines sit
    `leading` x the font's line height apart; a line falls `drop` px
    (default two line pitches). `colors` optionally gives one colour per line;
    `align` is 'center', 'left' or 'right' about `cx`. `kw` goes to
    `stack_arrivals`. Returns the Box of the finished block."""
    n = len(lines)
    pitch = vb.text.line_height(font) * leading
    drop = 2 * pitch if drop is None else drop
    arrivals = stack_arrivals(n, p, **kw)         # arrivals[k]: the k-th line up from the bottom
    bottom = cy + sum(arrivals) * pitch / 2       # the block's live height keeps it centred
    widths = [vb.text.measure(t, font) for t in lines]
    for k, a in enumerate(arrivals):
        if a <= 0:
            continue
        i = n - 1 - k
        w = widths[i]
        x = {'center': cx - w / 2, 'left': cx, 'right': cx - w}[align]
        y = bottom - (k + 1) * pitch - (1 - a) * drop
        vb.text.draw(cv, [lines[i]], font, x, y, colors[i] if colors else color, alpha=vb.clamp01(a * 1.5))
    full = max(widths, default=0)
    left = {'center': cx - full / 2, 'left': cx, 'right': cx - full}[align]
    return vb.Box(left, cy - n * pitch / 2, full, n * pitch)


LINES = ('STACK',) * 6


def draw(n, cv):
    f = demo.font(78, 900)
    colors = [demo.ACCENT] + [demo.INK] * (len(LINES) - 1)
    box = draw_stacked_lines(cv, LINES, f, demo.W / 2, demo.H / 2, demo.phase(n, 0.2, 2.4), demo.INK,
                             colors=colors, leading=0.7)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='stacked-line-build',
    name='Stacked line build',
    family='typography',
    group='Layout and poster',
    aliases=('layered line stack', 'type stack build', 'line stack'),
    definition='Lines of type drop in one after another, each settling on top of the last, '
               'until they pile up into a solid block of words.',
    phrasings=('stack the word line by line until it fills a block',
               'each new line of text lands on top of the one before it',
               'build up a tower of repeated headlines one row at a time'),
    related=('shape-stacking-drop', 'stacked-bar-build', 'pyramid-build', 'line-weave',
             'sticky-card-stack-on-scroll', 'voxel-build'),
    api=('videobuilder.capabilities.typography.stacked_line_build.draw_stacked_lines',
         'videobuilder.capabilities.typography.stacked_line_build.stack_arrivals'),
    demo=lambda: demo.film(draw),
)
