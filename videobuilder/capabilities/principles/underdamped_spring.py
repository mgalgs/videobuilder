"""Underdamped Spring: the same idea as Spring Motion (`spring-motion.py`),
which keeps the capability -- both only name `vb.spring` at a damping ratio
below 1 and demo the same overshoot and ring-down. This module's own code
stays (a film may still import it), but it is no longer a capability of its
own."""
import math

import videobuilder as vb

from .. import _demo as demo

MERGED_INTO = 'spring-motion'

PARAMS = vb.damped(0.14, hz=1.5)  # well under 1: several visible swings before it settles
RELEASE = 0.35  # seconds


def coil(cv, x, y0, y1, turns=8, half=16, color=demo.MUTED):
    """A zigzag spring hanging from (x, y0) down to (x, y1)."""
    lead = 10
    pts = [(x, y0), (x, y0 + lead)]
    span = (y1 - y0) - 2 * lead
    for i in range(1, 2 * turns):
        pts.append((x + (half if i % 2 else -half), y0 + lead + span * i / (2 * turns)))
    pts += [(x, y1 - lead), (x, y1)]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        cv.line(ax, ay, bx, by, color, width=3)


def draw(n, cv):
    t = max(0.0, n / demo.FPS - RELEASE)
    p = vb.spring(t, **PARAMS)
    W, H = demo.W, demo.H

    # Left: a weight on a spring, pulled up and let go.
    x, anchor, r = W * 0.24, H * 0.12, 26
    start, rest = H * 0.36, H * 0.56
    y = start + (rest - start) * p
    cv.rect(x - 60, anchor - 8, 120, 8, demo.MUTED, radius=3)
    coil(cv, x, anchor, y - r)
    cv.line(x - 85, rest, x + 85, rest, demo.MUTED, width=2, alpha=0.5)  # where it comes to rest
    demo.dot(cv, x, y, r)
    cv.mark('weight', x - r, y - r, 2 * r, 2 * r)

    # Right: the same motion traced against time.
    gx, gw, seconds = W * 0.46, W * 0.46, demo.SECONDS - RELEASE
    cv.line(gx, start - 20, gx, rest + (rest - start) + 20, demo.MUTED, width=2, alpha=0.5)
    cv.line(gx, rest, gx + gw, rest, demo.MUTED, width=2, alpha=0.5)
    steps = max(1, int(t / seconds * 240))
    prev = (gx, start)
    for i in range(1, steps + 1):
        s = min(t, seconds) * i / steps
        pt = (gx + gw * s / seconds, start + (rest - start) * vb.spring(s, **PARAMS))
        cv.line(*prev, *pt, demo.ACCENT, width=3)
        prev = pt
    demo.dot(cv, prev[0], prev[1], 6, color=demo.INK)
    cv.line(x + r + 8, y, prev[0] - 10, prev[1], demo.MUTED, width=1, alpha=0.35)  # ties weight to trace
