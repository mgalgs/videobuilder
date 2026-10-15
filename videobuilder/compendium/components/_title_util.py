"""Small helpers the title components share: the shot's own beat length,
fitting a title to a box, and a paper grain pass. Not a component (the
leading underscore keeps it out of the catalog)."""
import cairo

import videobuilder as vb
from videobuilder import text


def frames_per_beat(shot):
    """Frames a beat at whatever tempo the shot's film runs at (the preview's
    120 bpm or a recipe's own), read off the segment rather than assumed."""
    beats = shot.segment.until - shot.segment.at
    return shot.length / beats if beats > 0 else 15.0


def fit(title, make_font, w, h, sizes, balance=True):
    """(font, lines) at the largest size in `sizes` whose wrapped block fits
    `w` x `h`; the smallest size if none does. `make_font(size)` builds it."""
    for size in sizes:
        f = make_font(size)
        lines = text.wrap(title, f, w, balance=balance)
        bw, bh = text.block_size(lines, f)
        if bw <= w and bh <= h and all(text.measure(ln, f) <= w for ln in lines):
            return f, lines
    f = make_font(sizes[-1])
    return f, text.wrap(title, f, w, balance=balance)


def grain(cv, alpha, seed=1):
    """Paper texture over whatever the current clip allows."""
    ctx = cv.ctx
    ctx.set_source(vb.paper_grain(cv.width, cv.height, seed=seed))
    ctx.set_operator(cairo.OPERATOR_SOFT_LIGHT)
    ctx.paint_with_alpha(alpha)
    ctx.set_operator(cairo.OPERATOR_OVER)
