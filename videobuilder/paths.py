"""Path tools: partial reveal, arc-length resampling, morphing between two
point lists, and seeded hand jitter -- pure geometry on point lists, plus a
small helper to draw one onto a Canvas. No variable-width ribbons.

A "point list" is a sequence of (x, y) film-px pairs, open (a polyline) or
closed (its last point implicitly joins back to its first).
"""
import math
import random

import cairo

from .canvas import rgba
from .ease import clamp01


def _seg_lengths(points, closed):
    n = len(points)
    hops = range(n) if closed else range(n - 1)
    out = []
    for i in hops:
        x0, y0 = points[i]
        x1, y1 = points[(i + 1) % n]
        out.append(math.hypot(x1 - x0, y1 - y0))
    return out


def length(points, closed=False):
    """Total arc length of a point list (the closing hop included when `closed`)."""
    return sum(_seg_lengths(points, closed))


def reveal(points, fraction, closed=False):
    """The leading `fraction` (0..1, clamped) of `points` by arc length, as a
    new point list ending exactly at that length -- the last point is
    interpolated on whichever hop crosses the target length. `fraction <= 0`
    is `[]`; `fraction >= 1` is the whole path (with the closing point
    appended when `closed`)."""
    if not points:
        return []
    fraction = clamp01(fraction)
    pts = list(points) + ([points[0]] if closed else [])
    if fraction <= 0:
        return []
    lengths = _seg_lengths(points, closed)
    total = sum(lengths)
    if total == 0 or fraction >= 1:
        return pts
    target = total * fraction
    out = [pts[0]]
    acc = 0.0
    for i, hop in enumerate(lengths):
        if acc + hop >= target:
            t = (target - acc) / hop if hop > 0 else 0.0
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
            return out
        acc += hop
        out.append(pts[i + 1])
    return out


def resample(points, n, closed=False):
    """`n` (>= 2) points evenly spaced by arc length along `points`. An open
    path keeps its first and last point exactly; a closed one wraps evenly
    starting at `points[0]`. A degenerate (zero-length) path repeats its
    first point."""
    if n < 2:
        raise ValueError('resample needs at least 2 points')
    lengths = _seg_lengths(points, closed)
    total = sum(lengths)
    pts = list(points) + ([points[0]] if closed else [])
    if total == 0:
        return [points[0]] * n
    step = total / (n if closed else n - 1)
    out = []
    seg_i, seg_start = 0, 0.0
    for k in range(n):
        target = min(k * step, total)
        while seg_i < len(lengths) - 1 and seg_start + lengths[seg_i] < target - 1e-9:
            seg_start += lengths[seg_i]
            seg_i += 1
        hop = lengths[seg_i]
        t = clamp01((target - seg_start) / hop) if hop > 0 else 0.0
        x0, y0 = pts[seg_i]
        x1, y1 = pts[seg_i + 1]
        out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    return out


def _winding(points):
    """Twice the signed area (shoelace): sign gives a closed polygon's orientation."""
    area = 0.0
    n = len(points)
    for i in range(n):
        x0, y0 = points[i]
        x1, y1 = points[(i + 1) % n]
        area += x0 * y1 - x1 * y0
    return area


def _align(ref, points, closed):
    """Rotate (and reverse if its winding differs from `ref`'s) a resampled
    closed point list so its index 0 best matches `ref`'s: without this, two
    outlines resampled independently start at arbitrary points and a morph
    between them visibly twists or crosses instead of travelling the short
    way round. Open paths are returned as given -- they already share fixed
    endpoints."""
    if not closed or len(points) < 3:
        return points
    if (_winding(ref) >= 0) != (_winding(points) >= 0):
        points = list(reversed(points))
    best_k, best_d = 0, math.inf
    for k in range(len(points)):
        d = sum((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2
                for a, b in zip(ref, points[k:] + points[:k]))
        if d < best_d:
            best_d, best_k = d, k
    return points[best_k:] + points[:best_k]


def morph(a, b, t, closed=False, n=None):
    """Interpolate between point lists `a` and `b` at `t` in [0, 1] (clamped).
    Both are resampled to the same point count (`n`, default the longer of
    the two) by arc length; for a closed shape, the resampled `b` is rotated
    to the start point (and reversed if its winding differs) that best
    matches the resampled `a`'s, so corresponding points travel the short way
    round rather than visibly twisting. `t=0` is `a` resampled; `t=1` is `b`
    resampled and aligned."""
    n = n or max(len(a), len(b))
    ra = resample(a, n, closed)
    rb = _align(ra, resample(b, n, closed), closed)
    t = clamp01(t)
    return [(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t) for (x0, y0), (x1, y1) in zip(ra, rb)]


def jitter(points, seed, amount=1.0, wander=0.3):
    """`points` nudged by a small seeded wander, for a hand-drawn stroke:
    deterministic for a given `seed`, so the same stroke jitters the same way
    every frame it's drawn. `amount`: px of offset. `wander`: how quickly the
    offset changes point to point (low: a lazy drift; near 1: shaky)."""
    rnd = random.Random(seed)
    out = []
    ox = oy = 0.0
    for x, y in points:
        ox += (rnd.uniform(-1, 1) - ox) * wander
        oy += (rnd.uniform(-1, 1) - oy) * wander
        out.append((x + ox * amount, y + oy * amount))
    return out


def draw(cv, points, color, width=2, closed=False, fill=False, alpha=1.0):
    """Draw a point list onto `cv` as one path: straight hops between
    consecutive points. `fill`: filled solid (closing the path regardless of
    `closed`); otherwise stroked `width` px wide with round joins/caps,
    closed back to the first point when `closed`."""
    if len(points) < 2:
        return
    c = cv.ctx
    c.new_path()
    c.move_to(*points[0])
    for p in points[1:]:
        c.line_to(*p)
    if closed or fill:
        c.close_path()
    c.set_source_rgba(*rgba(color, alpha))
    if fill:
        c.fill()
    else:
        c.set_line_width(width)
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        c.set_line_join(cairo.LINE_JOIN_ROUND)
        c.stroke()
