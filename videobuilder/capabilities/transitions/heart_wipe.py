"""Heart Wipe: the incoming scene shows through a heart-shaped hole that opens
at the centre of the frame and swells until it covers the whole picture."""
import math
from functools import lru_cache

import videobuilder as vb
from videobuilder import paths

from .. import _demo as demo
from ..schema import Technique

N = 160         # points on the heart outline
MID = -2.6      # the classic heart curve's vertical middle, so it grows about its own centre


def heart_points(cx, cy, size, n=N):
    """A closed heart outline as `n` points, centred on (cx, cy), about
    `size` px across (the classic parametric heart: two lobes, a dip at the
    top, a point at the bottom)."""
    s = size / 32
    out = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        out.append((cx + s * x, cy - s * (y - MID)))
    return out


def _inside(pts, x, y):
    hit = False
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            hit = not hit
    return hit


@lru_cache(maxsize=64)
def cover_size(w, h, cx, cy):
    """The smallest heart `size` (as `heart_points` takes it) centred on
    (cx, cy) whose outline contains the whole w x h frame -- the top dip is
    what decides it."""
    edge = [(w * i / 24, 0) for i in range(25)] + [(w * i / 24, h) for i in range(25)] + \
           [(0, h * i / 24) for i in range(25)] + [(w, h * i / 24) for i in range(25)]
    lo, hi = 1.0, 8 * math.hypot(w, h)
    for _ in range(30):
        mid = (lo + hi) / 2
        pts = heart_points(cx, cy, mid)
        lo, hi = (lo, mid) if all(_inside(pts, x, y) for x, y in edge) else (mid, hi)
    return hi * 1.02


def heart_wipe(cv, a, b, p, center=None, ease=vb.ease_in_expo, rim=None, rim_width=10):
    """Draw the wipe at progress `p` (0 -> 1): `a(cv)` full frame, with `b(cv)`
    showing through a heart that grows from nothing at `center` (default the
    frame's centre) until it covers the frame at `p` = 1. `rim`: a colour to
    outline the heart's edge with while it grows (thinning out as it nears
    full size), or None for a clean cut.

    In a film, call it inside an overlap, e.g.
    `heart_wipe(cv, lambda c: old_shot(c), lambda c: new_shot(c), f / overlap_frames)`."""
    W, H = cv.width, cv.height
    cx, cy = center or (W / 2, H / 2)
    q = ease(vb.clamp01(p))
    a(cv)
    if q <= 0:
        return
    pts = heart_points(cx, cy, cover_size(W, H, cx, cy) * q)
    ctx = cv.ctx
    ctx.save()
    ctx.new_path()
    ctx.move_to(*pts[0])
    for pt in pts[1:]:
        ctx.line_to(*pt)
    ctx.close_path()
    ctx.clip()
    b(cv)
    ctx.restore()
    if rim is not None and q < 1:
        paths.draw(cv, pts, rim, width=rim_width * (1 - q) + 1, closed=True, alpha=1 - q ** 3)


TECHNIQUE = Technique(
    id='heart-wipe',
    name='Heart wipe',
    family='transitions',
    group='Wipes',
    aliases=('heart iris', 'heart reveal', 'heart-shaped wipe'),
    definition='A small heart opens in the middle of the old shot and swells until the new shot, '
               'seen through it, fills the whole frame.',
    phrasings=('reveal the next scene through a growing heart',
               'a heart-shaped iris out into the next shot',
               'have a heart open up and show the new clip inside it'),
    related=('like-heart-burst', 'circular-clip-reveal', 'logo-mask-wipe-reveal', 'paint-brush-wipe',
             'text-mask-reveal', 'wipe-reveal'),
    api=('videobuilder.techniques.transitions.heart_wipe.heart_wipe',
         'videobuilder.techniques.transitions.heart_wipe.heart_points'),
    demo=lambda: demo.two_scenes(lambda cv, a, b, p: heart_wipe(cv, a, b, p, rim=demo.ACCENT),
                                 start=0.7, length=1.6),
)
