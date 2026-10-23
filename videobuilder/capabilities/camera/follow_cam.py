"""Follow Cam: the camera chases a moving subject with a little smoothed lag,
so the subject stays near the middle of the frame while the world streams past."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def follow_cam(target, t, lag=0.2, fps=30, start=0.0):
    """Where a follow camera looks at `t` seconds: the point `target(t) -> (x, y)`
    run through an exponential smoother with time constant `lag` seconds, starting
    locked on `target(start)`. Bigger `lag` trails further behind on fast moves and
    takes longer to settle when the subject stops; `lag=0` is a rigid lock.

    Stateless (it re-runs the smoother from `start` at `fps` steps), so any frame
    renders alone. Draw the world shifted by `(W / 2 - x, H / 2 - y)` to centre it."""
    x, y = target(start)
    if lag <= 0:
        return target(t)
    steps = max(0, math.ceil((t - start) * fps))
    k = 1 - math.exp(-1 / (fps * lag))
    for i in range(1, steps + 1):
        tx, ty = target(min(t, start + i / fps))
        x += (tx - x) * k
        y += (ty - y) * k
    return x, y


# ---- demo: a top-down chase along a winding road ----

SECONDS = 5.0
TRAVEL = 1800  # world px the subject covers
LAG = 0.14  # trails ~100 px at cruise, settles well before the end


def _road_y(x):
    return 260 * math.sin(x / 520) + 120 * math.sin(x / 190 + 1.3)


def _subject(t):
    p = vb.clamp01((t - 0.4) / 3.6)
    x = TRAVEL * p * p * (3 - 2 * p)  # rolls off, cruises, pulls up
    return x, _road_y(x)


_rnd = random.Random(7)
_BLOCKS = [(x + _rnd.uniform(-60, 60), side * _rnd.uniform(170, 420), _rnd.uniform(60, 130),
            _rnd.uniform(60, 130), _rnd.choice((demo.TEAL, '#6f7cf0', demo.MUTED)))
           for x in range(-600, TRAVEL + 700, 150) for side in (-1, 1)]
_ROAD = [(x, _road_y(x)) for x in range(-900, TRAVEL + 1000, 12)]


def _world(cv, sx, sy):
    grid = 120
    for gx in range(int((-900) // grid) * grid, TRAVEL + 1000, grid):
        cv.line(gx, -1200, gx, 1200, demo.LINE, width=2)
    for gy in range(-1200, 1201, grid):
        cv.line(-900, gy, TRAVEL + 1000, gy, demo.LINE, width=2)
    vb.paths.draw(cv, _ROAD, '#23252c', width=150)
    vb.paths.draw(cv, _ROAD, demo.MUTED, width=4, alpha=0.5)
    for bx, off, bw, bh, color in _BLOCKS:
        by = _road_y(bx) + off
        cv.rect(bx - bw / 2 + 10, by - bh / 2 + 14, bw, bh, '#000000', radius=10, alpha=0.35)
        cv.rect(bx - bw / 2, by - bh / 2, bw, bh, color, radius=10)
    cv.sector(sx + 6, sy + 10, 40, 0, 2 * math.pi, '#000000', alpha=0.35)
    demo.dot(cv, sx, sy, 40)


def _minimap(cv, cam, subj):
    # top-left, well clear of the subject, which never strays far from the centre
    x0, y0, mw, mh, pad = 40, 40, 240, 130, 12
    left = -demo.W / 2 - 60  # the span the camera's frame sweeps, so it fits too
    s = (mw - 2 * pad) / (TRAVEL + demo.W + 120)
    cv.rect(x0, y0, mw, mh, demo.BG, radius=12, alpha=0.85)
    cv.outline(x0, y0, mw, mh, demo.MUTED, width=2, radius=12, alpha=0.6)
    to = lambda x, y: (x0 + pad + (x - left) * s, y0 + mh / 2 + y * s)  # noqa: E731
    road = [to(x, y) for x, y in _ROAD if left <= x <= left + (mw - 2 * pad) / s]
    vb.paths.draw(cv, road, demo.MUTED, width=3, alpha=0.6)
    fx, fy = to(cam[0] - demo.W / 2, cam[1] - demo.H / 2)
    cv.outline(fx, fy, demo.W * s, demo.H * s, demo.INK, width=2)
    demo.dot(cv, *to(*subj), r=6)


def _reticle(cv):
    cx, cy, r, arm = demo.W / 2, demo.H / 2, 78, 26
    for dx in (-1, 1):
        for dy in (-1, 1):
            cv.line(cx + dx * r, cy + dy * r, cx + dx * (r - arm), cy + dy * r, demo.INK, width=4, alpha=0.7)
            cv.line(cx + dx * r, cy + dy * r, cx + dx * r, cy + dy * (r - arm), demo.INK, width=4, alpha=0.7)


def draw(n, cv):
    t = n / demo.FPS
    sx, sy = _subject(t)
    cam = follow_cam(_subject, t, lag=LAG)
    with cv.layer(dx=demo.W / 2 - cam[0], dy=demo.H / 2 - cam[1]):
        _world(cv, sx, sy)
    cv.mark('subject', sx - cam[0] + demo.W / 2 - 40, sy - cam[1] + demo.H / 2 - 40, 80, 80)
    _reticle(cv)
    _minimap(cv, cam, (sx, sy))


CAPABILITY = Capability(
    id='follow-cam',
    name='Follow cam',
    family='camera',
    group='Camera moves',
    aliases=('chase cam', 'trailing camera', 'tracking camera'),
    definition='The view chases a moving subject a beat behind it, so the subject stays roughly '
               'centred while the scenery slides past around it.',
    phrasings=('keep the camera on the ball as it travels',
               'have the shot chase the character down the road',
               'track the moving dot so it stays in the middle'),
    related=('zoom-through', 'player-movement-trail', 'video-feedback-loop', 'reverse-motion-cut',
             'follow-through', 'motion-blur'),
    api=('videobuilder.capabilities.camera.follow_cam.follow_cam',),
    demo=lambda: demo.film(draw, SECONDS),
)
