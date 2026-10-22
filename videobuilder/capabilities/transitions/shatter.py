"""Shatter: the outgoing scene cracks like a pane of glass struck at one
point, then breaks into shards that burst outward and fall away, uncovering
the incoming scene behind it."""
import math
import random
from functools import lru_cache

from ...canvas import rgba
from .. import _demo as demo
from ..schema import Capability


def _clip(pts, w, h):
    """`pts` cut to the rectangle 0..w x 0..h (Sutherland-Hodgman)."""
    edges = ((lambda q: q[0] >= 0, 0, 0), (lambda q: q[0] <= w, 0, w),
             (lambda q: q[1] >= 0, 1, 0), (lambda q: q[1] <= h, 1, h))
    for inside, axis, v in edges:
        out = []
        for i, q in enumerate(pts):
            r = pts[i - 1]
            if inside(q) != inside(r):
                f = (v - r[axis]) / (q[axis] - r[axis])
                out.append((r[0] + f * (q[0] - r[0]), r[1] + f * (q[1] - r[1])))
            if inside(q):
                out.append(q)
        pts = out
        if not pts:
            break
    return pts


@lru_cache(maxsize=32)
def shards(w, h, cx, cy, spokes=14, rings=5, seed=0):
    """The pieces a `w` x `h` pane breaks into when struck at (cx, cy): a
    tuple of `(points, centroid, dist)` where `points` is the shard's closed
    outline, `centroid` its centre and `dist` 0 -> 1 how far it lies from the
    impact. Cracks run out from the impact on `spokes` jittered lines, cut
    across by `rings` jittered rings, smaller near the impact; the pieces tile
    the pane exactly (cut to its edges), and the same arguments always give the same pieces."""
    rnd = random.Random(seed)
    reach = 1.15 * max(math.hypot(x - cx, y - cy) for x in (0, w) for y in (0, h))
    step = 2 * math.pi / spokes
    angles = [i * step + rnd.uniform(-0.35, 0.35) * step for i in range(spokes)]
    # radii[i][j]: where ring j crosses spoke i -- shared by the shards either side, so they meet
    radii = [[0.0] + [reach * ((j + rnd.uniform(-0.3, 0.3)) / rings) ** 1.6 for j in range(1, rings)] + [reach]
             for _ in range(spokes)]
    out = []
    for i in range(spokes):
        k = (i + 1) % spokes
        a0, a1 = angles[i], angles[k] + (2 * math.pi if k == 0 else 0)
        for j in range(rings):
            pts = []
            for a, r in ((a0, radii[i][j]), (a0, radii[i][j + 1]), (a1, radii[k][j + 1]), (a1, radii[k][j])):
                p = (cx + r * math.cos(a), cy + r * math.sin(a))
                if not pts or p != pts[-1]:
                    pts.append(p)
            pts = _clip(pts, w, h)
            if len(pts) < 3:
                continue
            gx = sum(p[0] for p in pts) / len(pts)
            gy = sum(p[1] for p in pts) / len(pts)
            out.append((tuple(pts), (gx, gy), (j + 0.5) / rings))
    return tuple(out)


def _path(c, pts):
    c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    c.close_path()


def shatter(cv, a, b, p, at=None, crack=0.2, spokes=14, rings=5, seed=0, edge='#ffffff'):
    """Draw the shatter at progress `p` (0 -> 1): for the first `crack` of it
    `a(cv)` holds while cracks race out from the impact point `at` (default:
    a little off centre); then the pane breaks and its shards burst away from
    the impact and fall, spinning, nearest first, revealing `b(cv)`. `edge`
    colours the cracks and the shards' glinting edges.

    In a film, call it while two shots are live in an overlap, e.g.
    `shatter(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    w, h = cv.width, cv.height
    cx, cy = at if at is not None else (w * 0.56, h * 0.44)
    pieces = shards(w, h, round(cx), round(cy), spokes, rings, seed)
    c = cv.ctx
    if p < crack:
        a(cv)
        k = p / crack
        # each crack is drawn out from the impact as far as `k` reaches
        reach = max(math.hypot(x - cx, y - cy) for x in (0, w) for y in (0, h))
        c.save()
        c.arc(cx, cy, max(1.0, reach * k ** 0.7), 0, 2 * math.pi)
        c.clip()
        for pts, _, _ in pieces:
            _path(c, pts)
        c.set_source_rgba(*rgba(edge, 0.85))
        c.set_line_width(2.5)
        c.stroke()
        c.restore()
        cv.fill(edge, alpha=0.5 * max(0.0, 1 - k * 3))  # the flash of the hit
        return
    t = (p - crack) / (1 - crack)
    b(cv)
    c.push_group()
    a(cv)
    pane = c.pop_group()
    for idx, (pts, (gx, gy), dist) in enumerate(pieces):
        rnd = random.Random(seed * 1009 + idx)
        local = max(0.0, (t - 0.35 * dist) / (1 - 0.35 * dist))  # near the hit goes first
        dx, dy = gx - cx, gy - cy
        d = math.hypot(dx, dy) or 1.0
        burst = (900 * (1 - dist) + 250) * rnd.uniform(0.7, 1.2)
        ox = dx / d * burst * local
        oy = dy / d * burst * local - 350 * local + 2600 * local * local  # pop up, then fall
        spin = rnd.uniform(-1, 1) * 2.4 * local
        grow = 1 + 0.35 * (1 - dist) * local  # pieces near the hit fly toward the camera
        c.save()
        c.translate(gx + ox, gy + oy)
        c.rotate(spin)
        c.scale(grow, grow)
        c.translate(-gx, -gy)
        _path(c, pts)
        c.set_source(pane)
        c.fill_preserve()
        c.set_source_rgba(*rgba(edge, 0.7 if local > 0 else 0.85))
        c.set_line_width(2.5)
        c.stroke()
        c.restore()


CAPABILITY = Capability(
    id='shatter',
    name='Shatter',
    family='transitions',
    group='Shatter and Break',
    aliases=('glass shatter', 'glass break transition', 'shatter transition'),
    definition='The first scene cracks like a struck pane of glass and breaks into shards '
               'that burst outward and tumble away, uncovering the next scene behind it.',
    phrasings=('smash the screen like glass to get to the next shot',
               'the picture breaks into pieces that fall away',
               'crack the frame and let it shatter into the next scene'),
    related=('fracture-shatter', 'type-explosion', 'smash-cut', 'rain-on-glass', 'shake', 'exploded-view'),
    api=('videobuilder.capabilities.transitions.shatter.shatter',
         'videobuilder.capabilities.transitions.shatter.shards'),
    demo=lambda: demo.two_scenes(shatter, start=0.6, length=1.8),
)
