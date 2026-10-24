"""Impact Shake: the same videobuilder.impact.shake as Shake
(`../principles/shake.py`, which keeps the capability) -- a sharp jolt that
dies away within a fraction of a second, here applied to a word instead of
the whole frame. This module's own code stays (a film may still import
it), but it is no longer a capability of its own."""
from videobuilder import impact

from .. import _demo as demo

MERGED_INTO = 'shake'

HITS = (18, 40, 62)  # frames the word is struck on


def draw(n, cv):
    dx = dy = 0.0
    flash = 0.0
    for i, at in enumerate(HITS):
        sx, sy = impact.shake(n, at, frames=12, amount=34, seed=i)
        dx, dy = dx + sx, dy + sy
        if at <= n < at + 8:
            flash = max(flash, 1 - (n - at) / 8)
    x, y = demo.W / 2 + dx, demo.H / 2 + dy
    box = demo.word(cv, 'IMPACT', x, y, size=150, weight=900)
    if flash:  # the word blushes accent as it is struck
        demo.word(cv, 'IMPACT', x, y, size=150, weight=900, color=demo.ACCENT, alpha=flash)
    cv.mark('text', *box)
