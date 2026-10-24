"""Spiral Bloom: the same idea as Phyllotaxis (`../particles/phyllotaxis.py`,
which keeps the capability) -- both add shapes one by one at the golden
angle, each pushed out a little further than the last, so they unfurl into
the same interlocking sunflower spiral arms. This module's own code stays
(a film may still import it), but it is no longer a capability of its
own."""
import math

import videobuilder as vb

from .. import _demo as demo

MERGED_INTO = 'phyllotaxis'

GOLDEN_ANGLE = math.pi * (3 - math.sqrt(5))  # ~137.5 degrees: the turn between neighbouring seeds


def spiral_bloom(count, p, radius, turn=GOLDEN_ANGLE, twist=1.2, spin=0.35, stagger=0.6):
    """`count` petals at bloom progress `p` (0 -> 1) as `(dx, dy, size, angle)`
    tuples, offsets from the centre, innermost first. Petal `i` sits at angle
    `i * turn` and distance `radius * sqrt(i / count)` (an even-spaced seed
    head). Petals start in order from the centre out across the first
    `stagger` of the bloom; each swings out from the centre along its arm,
    unwinding `twist` radians as it goes, and grows from 0 to `size` 1 with a
    small overshoot. The whole head turns `spin` radians across the bloom.
    `angle` points away from the centre, for drawing elongated petals."""
    p = vb.clamp01(p)
    out = []
    for i in range(count):
        f = (i + 0.5) / count
        start = stagger * i / max(count - 1, 1)
        q = vb.clamp01((p - start) / (1 - stagger)) if stagger < 1 else float(p >= start)
        if q <= 0:
            continue
        reach = vb.ease_out_quint(q)
        a = i * turn + spin * p + twist * (1 - reach)
        r = radius * math.sqrt(f) * reach
        out.append((r * math.cos(a), r * math.sin(a), vb.ease_out_back(q), a))
    return out


def draw_spiral_bloom(cv, cx, cy, p, count=140, radius=200, petal=14, colors=(demo.ACCENT, demo.TEAL), arms=13,
                      **kw):
    """Draw a spiral bloom of `count` petals centred at (cx, cy) at progress
    `p`: each petal an ellipse pointed outwards, larger towards the rim,
    coloured by which of `arms` spiral arms it falls on (13 and 21 are the
    arms the golden angle makes visible), cycling through `colors`. `kw` goes
    to `spiral_bloom`."""
    ctx = cv.ctx
    for i, (dx, dy, s, a) in enumerate(spiral_bloom(count, p, radius, **kw)):
        size = petal * s * (0.45 + 0.75 * math.sqrt((i + 0.5) / count))
        if size <= 0:
            continue
        ctx.save()
        ctx.translate(cx + dx, cy + dy)
        ctx.rotate(a)
        ctx.scale(1.0, 0.55)
        cv.sector(0, 0, size, 0, 2 * math.pi, colors[i % arms % len(colors)], alpha=0.92)
        ctx.restore()


def draw(n, cv):
    cx, cy = demo.W / 2, demo.H / 2
    draw_spiral_bloom(cv, cx, cy, demo.phase(n, 0.2, 2.5), count=150, radius=210, petal=18,
                      colors=(demo.ACCENT, demo.TEAL, demo.INK))
    cv.mark('bloom', cx - 230, cy - 230, 460, 460)
