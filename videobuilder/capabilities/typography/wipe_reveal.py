"""Wipe Reveal: a straight edge travels across the text and the letters exist
only on the side it has already passed, so the words appear as if uncovered."""
import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

DIRECTIONS = ('right', 'left', 'down', 'up')


def wipe_reveal(cv, draw, box, p, direction='right', softness=0.0):
    """Draw `draw(cv)` revealed by a wipe at progress `p` (0 -> 1) across
    `box` (a `vb.Box` or `(x, y, w, h)`): nothing at 0, all of it at 1. The
    edge moves toward `direction` ('right' sweeps left to right; also 'left',
    'down', 'up'). `softness` feathers the edge over that fraction of the
    box's length along the sweep; 0 is a hard edge. Whatever `draw` paints
    outside `box` is never shown."""
    if direction not in DIRECTIONS:
        raise ValueError(f'direction must be one of {", ".join(DIRECTIONS)}, not {direction!r}')
    p = vb.clamp01(p)
    if p <= 0:
        return
    x, y, w, h = box
    if p >= 1:
        with cv.clip(x, y, w, h):
            draw(cv)
        return
    along = w if direction in ('right', 'left') else h
    feather = max(0.0, softness) * along
    lead = p * (along + feather)          # how far the leading (transparent) side of the edge has gone
    solid = lead - feather                # everything before this is fully shown
    c = cv.ctx
    with cv.clip(x, y, w, h):
        if feather <= 0:
            if direction == 'right':
                cell = (x, y, lead, h)
            elif direction == 'left':
                cell = (x + w - lead, y, lead, h)
            elif direction == 'down':
                cell = (x, y, w, lead)
            else:
                cell = (x, y + h - lead, w, lead)
            with cv.clip(*cell):
                draw(cv)
            return
        start, end = {'right': ((x + solid, 0), (x + lead, 0)),
                      'left': ((x + w - solid, 0), (x + w - lead, 0)),
                      'down': ((0, y + solid), (0, y + lead)),
                      'up': ((0, y + h - solid), (0, y + h - lead))}[direction]
        grad = cairo.LinearGradient(*start, *end)
        grad.add_color_stop_rgba(0, 0, 0, 0, 1)
        grad.add_color_stop_rgba(1, 0, 0, 0, 0)
        c.push_group()
        draw(cv)
        c.pop_group_to_source()
        c.mask(grad)


def wipe_lines(cv, lines, font, x, y, p, color, stagger=0.25, direction='right', softness=0.15,
               ease=vb.ease_in_out_quart, align='left', width=None):
    """Draw `lines` (a list of strings) from top-left (x, y), each line wiped
    on in turn at overall progress `p`: a line starts `stagger` of the way
    after the one above it and every line takes the same share. `ease`
    shapes each line's sweep. Returns the Box of the whole block."""
    lh = vb.text.line_height(font)
    bw = width or vb.text.block_size(lines, font)[0]
    span = 1 - stagger * (len(lines) - 1) if len(lines) > 1 else 1
    span = max(span, 1e-6)
    pad = lh * 0.2                       # room for descenders and overshoot outside the line box
    for i, line in enumerate(lines):
        q = ease(vb.clamp01((p - i * stagger) / span))
        ly = y + i * lh
        lw = vb.text.measure(line, font)
        lx = x + {'left': 0, 'center': (bw - lw) / 2, 'right': bw - lw}[align]
        wipe_reveal(cv, lambda c, s=line, lx=lx, ly=ly: vb.text.draw(c, [s], font, lx, ly, color),
                    (lx - pad, ly - pad, lw + 2 * pad, lh + 2 * pad), q, direction, softness)
    return vb.Box(x, y, bw, lh * len(lines))


def draw(n, cv):
    f = demo.font(120, 900)
    lines = ['WIPE ON', 'THE TITLE']
    w, h = vb.text.block_size(lines, f)
    x, y = (demo.W - w) / 2, (demo.H - h) / 2
    box = wipe_lines(cv, lines, f, x, y, demo.phase(n, 0.2, 2.5), demo.INK, stagger=0.3, align='center',
                     width=w)
    cv.mark('text', *box)


TECHNIQUE = Technique(
    id='wipe-reveal',
    name='Wipe reveal',
    family='typography',
    group='Per-unit reveals',
    aliases=('wipe on', 'linear wipe on text', 'mask wipe', 'soft wipe reveal'),
    definition='A straight, slightly soft edge slides across the words and they are visible only '
               'where it has already passed, so each line is uncovered from one side to the other.',
    phrasings=('wipe the title on from left to right',
               'have the text uncovered by a sweeping edge, one line after another',
               'the words appear as if a mask slides off them sideways'),
    related=('ink-spread-reveal', 'scanline-wipe', 'text-mask-reveal', 'underline-wipe', 'linear-wipe',
             'handwriting-reveal'),
    api=('videobuilder.techniques.typography.wipe_reveal.wipe_reveal',
         'videobuilder.techniques.typography.wipe_reveal.wipe_lines'),
    demo=lambda: demo.film(draw),
)
