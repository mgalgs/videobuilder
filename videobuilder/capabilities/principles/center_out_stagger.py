"""Center-Out Stagger: the one-dimensional case of Radial Stagger
(`radial_stagger.py`, which keeps the capability) -- starting from a point
and spreading by distance: a row of items starts moving from its middle,
and the start times ripple out symmetrically so the two ends go last.
This module's own code stays (a film may still import it), but it is no
longer a capability of its own."""
import videobuilder as vb

from .. import _demo as demo

MERGED_INTO = 'radial-stagger'


def center_out_delay(i, count):
    """Item `i` of `count` -> its start delay in [0, 1]: 0 for the middle item
    (both middles when `count` is even), 1 for the two ends, mirrored."""
    half = (count - 1) / 2
    return abs(i - half) / half if half > 0 else 0.0


def center_out_stagger(i, count, p, spread=0.6):
    """Local progress 0 -> 1 of item `i` of `count` at overall progress `p`.
    Every item takes `1 - spread` of the run; its start is offset by
    `spread * center_out_delay(i, count)`, so the middle moves first and the
    ends finish exactly at `p = 1`. Ease the result as you like."""
    span = 1 - spread
    return vb.clamp01((p - spread * center_out_delay(i, count)) / span)


def draw(n, cv):
    count, w, h, gap = 9, 72, 84, 18
    left = (demo.W - (count * w + (count - 1) * gap)) / 2 + w / 2
    low, high = demo.H / 2 + 70, demo.H / 2 - 50
    p = demo.phase(n, 0.4, 2.4)
    for i in range(count):
        x = left + i * (w + gap)
        cv.line(x - w / 2, low + h / 2 + 12, x + w / 2, low + h / 2 + 12, demo.LINE, width=3)  # where each starts
        q = vb.ease_out_back(center_out_stagger(i, count, p))
        demo.card(cv, x, low + (high - low) * q, w=w, h=h)
        cv.mark(f'item{i}', x - w / 2, low + (high - low) * q - h / 2, w, h)
