"""Linear Stagger: the same cascade as Staggered reveals
(`staggered_reveals.py`, which keeps the capability): the items of a list
run the same move, each one starting a fixed delay after the one before
it, so the motion travels down the list in order (or back up it,
reversed). This module's own code stays (a film may still import it),
but it is no longer a capability of its own."""
import videobuilder as vb

from .. import _demo as demo

MERGED_INTO = 'staggered-reveals'


def linear_stagger(p, i, count, spread=0.6, reverse=False):
    """Item `i` of `count`'s own progress (0 -> 1) at overall progress `p`
    (0 -> 1). Each item's move lasts `1 - spread` of the whole; the starts
    are spaced evenly across the first `spread`, so the first item starts at
    0 and the last finishes at 1. `reverse` runs the list from its end."""
    k = count - 1 - i if reverse else i
    start = spread * k / (count - 1) if count > 1 else 0.0
    return vb.clamp01((p - start) / (1 - spread)) if spread < 1 else float(p >= start)


COUNT, SIZE, GAP = 8, 60, 26


def draw(n, cv):
    # Up in order, a short hold, then back down reversed (last square first), so
    # the loop shows both directions and ends where it began. The gallery's
    # poster (70%, 2.1 s) lands mid-way through the reversed pass.
    x0 = (demo.W - COUNT * SIZE - (COUNT - 1) * GAP) / 2
    low, high = demo.H / 2 + 50, demo.H / 2 - 100
    rise, drop = demo.phase(n, 0.15, 1.35), demo.phase(n, 1.55, 2.85)
    for i in range(COUNT):
        x = x0 + i * (SIZE + GAP)
        cv.line(x + 6, low + SIZE + 14, x + SIZE - 6, low + SIZE + 14, demo.LINE, width=3)
        up = vb.ease_out_back(linear_stagger(rise, i, COUNT, spread=0.65))
        down = vb.ease_in_out_quart(linear_stagger(drop, i, COUNT, spread=0.6, reverse=True))
        y = low + (high - low) * (up - down)
        cv.rect(x, y, SIZE, SIZE, demo.ACCENT, radius=12)
        cv.mark(f'item{i}', x, y, SIZE, SIZE)
