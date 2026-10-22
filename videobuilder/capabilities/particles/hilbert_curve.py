"""Hilbert curve: one unbroken line that snakes through every cell of a square
grid, refining order by order -- each corner splits into four smaller turns
-- until it fills the square."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def _cell(d, side):
    """The (column, row) of step `d` along the Hilbert curve on a `side` x
    `side` grid (`side` a power of two)."""
    x = y = 0
    s = 1
    while s < side:
        rx = 1 & (d // 2)
        ry = 1 & (d ^ rx)
        if ry == 0:
            if rx == 1:
                x, y = s - 1 - x, s - 1 - y
            x, y = y, x
        x += s * rx
        y += s * ry
        d //= 4
        s *= 2
    return x, y


def hilbert_points(order, x, y, size):
    """The order-`order` (>= 1) Hilbert curve as a point list: the centres of
    a 2**order square grid filling the `size`-px square whose top-left is
    (x, y), in curve order. It starts bottom-left and ends bottom-right."""
    side = 2 ** order
    cell = size / side
    out = []
    for d in range(side * side):
        cx, cy = _cell(d, side)
        out.append((x + (cx + 0.5) * cell, y + size - (cy + 0.5) * cell))
    return out


def hilbert_at(level, x, y, size):
    """The Hilbert curve at a fractional `level` (>= 1): between whole orders
    each point of the coarser curve splits into the four points of the finer
    one that sit inside its cell, so the line visibly refines rather than
    jumping. `level=2.5` is halfway from order 2 to order 3."""
    level = max(1.0, level)
    lo = int(level)
    t = level - lo
    fine = hilbert_points(lo + 1, x, y, size) if t > 0 else None
    coarse = hilbert_points(lo, x, y, size)
    if fine is None:
        return coarse
    return [(cx + (fx - cx) * t, cy + (fy - cy) * t)
            for i, (fx, fy) in enumerate(fine) for cx, cy in [coarse[i // 4]]]


def draw_hilbert(cv, level, x, y, size, color, width=None, reveal=1.0, alpha=1.0):
    """Draw the Hilbert curve at `level` (see `hilbert_at`) in the `size`-px
    square at (x, y). `reveal` (0 -> 1) draws only the leading part of it by
    length, for a line that traces itself in. `width` defaults to a stroke
    that thins as the grid gets finer. Returns the square's Box."""
    pts = hilbert_at(level, x, y, size)
    if reveal < 1:
        pts = vb.paths.reveal(pts, reveal)
    w = width or max(2.0, size / 2 ** max(1.0, level) * 0.22)
    vb.paths.draw(cv, pts, color, width=w, alpha=alpha)
    return vb.Box(x, y, size, size)


def draw(n, cv):
    size = 400
    x, y = (demo.W - size) / 2, (demo.H - size) / 2 + 22
    cv.outline(x - 16, y - 16, size + 32, size + 32, demo.LINE, width=2, radius=12)
    trace = demo.phase(n, 0.15, 0.6)
    steps = 4 * demo.phase(n, 0.75, 2.75)  # orders 1 -> 5, each split eased on its own so every order holds a beat
    whole = min(int(steps), 3)
    level = 1 + whole + vb.ease_in_out_quart(steps - whole)
    box = draw_hilbert(cv, level, x, y, size, demo.ACCENT, reveal=trace)
    cv.mark('curve', *box)
    demo.word(cv, f'order {round(level)}', demo.W / 2, y - 42, size=24, color=demo.MUTED, weight=600)


TECHNIQUE = Technique(
    id='hilbert-curve',
    name='Hilbert curve',
    family='particles',
    group='Fractals',
    aliases=('Hilbert space-filling curve', 'space-filling curve', 'Peano-Hilbert curve'),
    definition='A single continuous line winds through every cell of a square grid, '
               'each step splitting its turns into four smaller copies until it fills the square.',
    phrasings=('a maze-like line that keeps subdividing until it covers the whole square',
               'draw a space-filling fractal path that gets denser and denser',
               'one line folding into tighter and tighter zigzags to fill a box'),
    related=('superformula-morph', 'isolines-contour-animation', 'line-to-polygon-transform',
             'marching-squares-contour', 'streamlines', 'sparkline-draw'),
    api=('videobuilder.techniques.particles.hilbert_curve.draw_hilbert',
         'videobuilder.techniques.particles.hilbert_curve.hilbert_at',
         'videobuilder.techniques.particles.hilbert_curve.hilbert_points'),
    demo=lambda: demo.film(draw),
)
