"""Shutter wipe: the same idea as Venetian blinds wipe (`venetian_blinds_wipe.py`),
which keeps the capability -- both cut the frame into strips that open on the
next scene, the only difference being all at once versus one after another,
which a stagger setting covers. This module's own code stays (a film may
still import it), but it is no longer a capability of its own."""
import videobuilder as vb

MERGED_INTO = 'venetian-blinds-wipe'


def shutter_wipe(cv, a, b, p, slats=8, vertical=True, stagger=0.6, reverse=False, ease=vb.ease_in_out_quart):
    """Draw the wipe at progress `p` (0 -> 1): `a(cv)` underneath, with `b(cv)`
    showing through `slats` parallel strips that each open from their own
    centre line out to full width.

    `vertical` cuts the frame into upright slats that open sideways (False:
    horizontal slats opening up and down). `stagger` is the share of the run
    spent starting one slat after the next (0: all open together, like blinds;
    near 1: one at a time); `reverse` starts from the right (or bottom) edge.
    `ease` shapes each slat's own opening.

    In a film, call it while two shots are live in an overlap, e.g.
    `shutter_wipe(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    W, H = cv.width, cv.height
    span = W if vertical else H
    size = span / slats
    stagger = min(max(stagger, 0.0), 0.95)
    own = 1 - stagger                           # each slat's share of the run
    a(cv)
    ctx = cv.ctx
    ctx.save()
    ctx.new_path()
    for i in range(slats):
        k = slats - 1 - i if reverse else i
        start = stagger * k / max(1, slats - 1)
        open_ = size * ease(vb.clamp01((p - start) / own))
        if size - open_ < 0.5:                  # snap sub-pixel gaps shut, or they show as hairlines
            open_ = size
        elif open_ < 0.5:
            open_ = 0
        lo = i * size + (size - open_) / 2
        if open_ > 0:
            ctx.rectangle(*((lo, 0, open_, H) if vertical else (0, lo, W, open_)))
    ctx.clip()  # one clip for every slat, so `b` draws once and open neighbours meet without a seam
    b(cv)
    ctx.restore()
