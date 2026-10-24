"""Overlapping Action: the same classic principle as Follow Through
(`follow_through.py`, which keeps the capability) -- loose parts trail,
swing past and settle after the body stops. The parts of one thing don't
move as a block: the lead part stops crisply while the parts hanging off
it start a beat later, swing past the stop and settle on their own time.
This module's own code stays (a film may still import it), but it is no
longer a capability of its own."""
import videobuilder as vb

from .. import _demo as demo

MERGED_INTO = 'follow-through'


def overlapping_action(t, i, parts, lag=0.06, hz=1.6, lead=1.0, tail=0.3):
    """Progress (0 -> 1, may overshoot) at `t` seconds of part `i` of `parts`
    making one move together. Part 0 is the lead; each later part starts
    `lag` seconds after the one before and rides a looser spring, its damping
    ratio running from `lead` (part 0) to `tail` (the last part), so the
    trailing parts arrive late, overshoot and wobble to rest after the lead
    has stopped. `hz` is every part's natural frequency."""
    k = i / (parts - 1) if parts > 1 else 0.0
    return vb.spring(t - i * lag, **vb.damped(lead + (tail - lead) * k, hz))


def draw(n, cv):
    # Across and back: the return lands at ~2.1 s, so the poster frame catches the card
    # stopped with the tassel still swinging past it, and the clip loops back to its start.
    parts, out, back = 5, 0.3, 1.6
    x0, x1, top = demo.W / 2 - 230, demo.W / 2 + 230, 130
    s = n / demo.FPS
    a, b, t = (x0, x1, s - out) if s < back else (x1, x0, s - back)
    xs = [a + (b - a) * overlapping_action(t, i, parts) for i in range(parts)]
    # Part 0 is the card; parts 1.. hang below it as a tassel, each bob a step further down the chain.
    pts = [(xs[0], top + 55)] + [(xs[i], top + 55 + 62 * i) for i in range(1, parts)]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        cv.line(ax, ay, bx, by, demo.MUTED, width=4)
    for i, (bx, by) in enumerate(pts[1:], 1):
        demo.dot(cv, bx, by, 22 - 2 * i, color=demo.TEAL)
    demo.card(cv, xs[0], top, w=180, h=110)
    left, right = min(x for x, _ in pts), max(x for x, _ in pts)
    cv.mark('tassel', left - 22, top - 55, right - left + 44, pts[-1][1] - top + 77)
