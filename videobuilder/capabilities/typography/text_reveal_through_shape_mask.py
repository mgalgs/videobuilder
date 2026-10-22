"""Text Reveal Through Shape Mask: a line of text that only shows inside a
shape -- a circle, a pill, any polygon -- so moving, growing or morphing the
shape is what reveals the letters."""
import math
from contextlib import contextmanager

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def circle(cx, cy, r, n=72):
    """A circle centred at (cx, cy) as a closed point list of `n` points, so it
    can be moved, scaled or morphed (`vb.paths.morph`) like any other shape."""
    return [(cx + r * math.cos(2 * math.pi * i / n - math.pi / 2),
             cy + r * math.sin(2 * math.pi * i / n - math.pi / 2)) for i in range(n)]


@contextmanager
def through_shape(cv, shape):
    """Everything drawn inside the block shows only within the closed point
    list `shape` (any polygon; fewer than three points shows nothing)."""
    c = cv.ctx
    c.save()
    c.new_path()
    if len(shape) >= 3:
        c.move_to(*shape[0])
        for p in shape[1:]:
            c.line_to(*p)
        c.close_path()
    else:
        c.rectangle(0, 0, 0, 0)
    c.clip()
    try:
        yield cv
    finally:
        c.restore()


def draw_text_through_shape(cv, text, font, x, y, color, shape, fill=None, fill_alpha=1.0,
                            edge=None, edge_alpha=0.6):
    """Draw `text` (one string or a list of lines) from its top-left (x, y),
    visible only inside the closed point list `shape`. `fill` paints the
    aperture first, behind the text; `edge` strokes its outline on top. Animate
    by passing a new `shape` each frame. Returns the Box of the full text."""
    lines = [text] if isinstance(text, str) else list(text)
    if fill is not None and len(shape) >= 3:
        vb.paths.draw(cv, shape, fill, fill=True, alpha=fill_alpha)
    with through_shape(cv, shape):
        vb.text.draw(cv, lines, font, x, y, color)
    if edge is not None:
        vb.paths.draw(cv, shape, edge, width=2, closed=True, alpha=edge_alpha)
    w, h = vb.text.block_size(lines, font)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    f = demo.font(104, 800)
    text = 'REVEAL'
    w, h = vb.text.block_size([text], f)
    x, y = (demo.W - w) / 2, (demo.H - h) / 2
    cy = demo.H / 2
    # A small window slides across the word, then settles in the middle and opens up to show all of it.
    scan = vb.ease_in_out_quart(demo.phase(n, 0.2, 1.6))
    grow = vb.ease_out_expo(demo.phase(n, 1.7, 2.5))
    r_small, r_big = 64, math.hypot(w / 2, h / 2) + 30  # just big enough to hold the whole word
    cx0, cx1 = x - 30, x + w + 30
    cx = cx0 + (cx1 - cx0) * scan
    cx += (demo.W / 2 - cx) * grow
    r = r_small + (r_big - r_small) * grow
    shape = circle(cx, cy, r)
    box = draw_text_through_shape(cv, text, f, x, y, demo.INK, shape,
                                  fill=demo.kit.mix(demo.BG, demo.TEAL, 0.18), edge=demo.TEAL)
    cv.mark('text', *box)
    cv.mark('aperture', cx - r, cy - r, 2 * r, 2 * r)


TECHNIQUE = Technique(
    id='text-reveal-through-shape-mask',
    name='Text reveal through shape mask',
    family='typography',
    group='Masking and clipping',
    aliases=('masked text reveal', 'shape knockout reveal', 'moving window reveal', 'sliding aperture text',
             'window scan through text'),
    definition='The words can only be seen through a shape, such as a circle sliding across them '
               'or opening up wider, so the letters appear wherever that window goes.',
    phrasings=('show the title through a moving circle, like a spotlight passing over it',
               'the text is hidden except inside a shape that grows to uncover it',
               'a little window slides along the word and then opens up to show the whole thing'),
    related=('text-mask-reveal', 'character-rise', 'typewriter-reveal', 'wipe-reveal', 'handwriting-reveal',
             'wireframe-reveal'),
    api=('videobuilder.techniques.typography.text_reveal_through_shape_mask.draw_text_through_shape',
         'videobuilder.techniques.typography.text_reveal_through_shape_mask.through_shape',
         'videobuilder.techniques.typography.text_reveal_through_shape_mask.circle'),
    demo=lambda: demo.film(draw),
)
