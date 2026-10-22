"""Like heart burst: an outlined heart is pressed, fills with colour as it pops
back past full size, and throws off a ring and a spray of dots and tiny hearts
that fly outward and fade."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

PALETTE = (demo.ACCENT, '#f2b134', demo.TEAL, '#8f7cf0', demo.INK)


def heart_points(cx, cy, size, n=72):
    """A heart `size` px wide centred at (cx, cy), as a closed point list
    (the classic parametric heart, point down)."""
    k = size / 34
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + x * k, cy - (y + 2.5) * k))
    return pts


def heart(cv, cx, cy, size, color, fill=True, width=4, alpha=1.0):
    """Draw a heart `size` px wide at (cx, cy): filled, or outlined `width` px."""
    vb.paths.draw(cv, heart_points(cx, cy, size), color, width=width, closed=True, fill=fill, alpha=alpha)


def like_heart_burst(cv, cx, cy, size, p, color=demo.ACCENT, idle=demo.INK, colors=PALETTE,
                     count=16, seed=0, reach=1.15):
    """Draw a like heart `size` px wide at (cx, cy) at burst progress `p`.

    `p` <= 0 is the idle outline (in `idle`); 0 -> 0.12 presses it smaller;
    then it fills with `color` and pops back with an overshoot, while a thin
    ring and `count` particles (dots and tiny hearts in `colors`) fly out to
    about `reach` x `size` from the centre and fade by `p` = 1. Hold `p` at 1
    for the liked state. The same `seed` gives the same spray."""
    p = max(0.0, p)
    if p <= 0:
        heart(cv, cx, cy, size, idle, fill=False, width=max(2, size / 24))
        return
    press = min(1.0, p / 0.12)
    if p < 0.12:
        s = 1 - 0.22 * math.sin(press * math.pi / 2)
        heart(cv, cx, cy, size * s, idle, fill=False, width=max(2, size / 24))
        return
    q = vb.clamp01((p - 0.12) / 0.45)  # pop: 0.78 -> 1.2 fast, then settle back to 1
    s = 0.78 + 0.42 * vb.ease_out_expo(q / 0.4) if q < 0.4 else 1.2 - 0.2 * vb.ease_in_out_quart((q - 0.4) / 0.6)

    ring = vb.clamp01((p - 0.12) / 0.35)
    if ring < 1:
        r = size * (0.35 + 0.75 * (1 - (1 - ring) ** 3))
        cv.arc(cx, cy, r, 0, 2 * math.pi, color, width=max(1, size * 0.09 * (1 - ring)), alpha=1 - ring)

    rnd = random.Random(seed)
    fly = vb.clamp01((p - 0.14) / 0.86)
    out = 1 - (1 - fly) ** 3
    fade = 1 - vb.clamp01((fly - 0.35) / 0.65)
    for i in range(count):
        a = 2 * math.pi * (i + rnd.uniform(-0.3, 0.3)) / count - math.pi / 2
        d = size * (0.4 + reach * rnd.uniform(0.75, 1.1) * out)
        px, py = cx + d * math.cos(a), cy + d * math.sin(a) + size * 0.15 * fly * fly
        c = colors[i % len(colors)]
        if fade <= 0:
            continue
        if i % 3 == 0:
            heart(cv, px, py, size * 0.16 * (0.5 + 0.5 * fade), c, alpha=fade)
        else:
            demo.dot(cv, px, py, size * rnd.uniform(0.035, 0.06) * (0.4 + 0.6 * fade), color=c, alpha=fade)

    heart(cv, cx, cy, size * s, color)


def _cursor(cv, x, y, down=False):
    k = 0.85 if down else 1.0
    pts = [(0, 0), (0, 26), (7, 20), (12, 31), (17, 29), (12, 18), (21, 18)]
    pts = [(x + px * k, y + py * k) for px, py in pts]
    vb.paths.draw(cv, pts, demo.INK, closed=True, fill=True)
    vb.paths.draw(cv, pts, demo.BG, width=2, closed=True)


def draw(n, cv):
    cx, cy, size = demo.W / 2, demo.H / 2, 150
    tile = 260
    cv.shadow(cx - tile / 2, cy - tile / 2, tile, tile, radius=28, dy=8, blur=24, color=(0, 0, 0, 0.4))
    cv.rect(cx - tile / 2, cy - tile / 2, tile, tile, '#1d1f26', radius=28)
    cv.outline(cx - tile / 2, cy - tile / 2, tile, tile, demo.LINE, width=2, radius=28)
    like_heart_burst(cv, cx, cy + 4, size, demo.phase(n, 0.9, 2.5), seed=3)
    cv.mark('heart', cx - size / 2, cy - size / 2, size, size)
    m = vb.ease_in_out_quart(demo.phase(n, 0.2, 0.85))
    back = vb.ease_in_out_quart(demo.phase(n, 1.6, 2.3))
    x = cx + 190 - 175 * m + 175 * back
    y = cy + 150 - 140 * m + 140 * back
    _cursor(cv, x, y, down=0.9 <= n / demo.FPS < 1.05)


CAPABILITY = Capability(
    id='like-heart-burst',
    name='Like heart burst',
    family='ui',
    group='Toggles & controls',
    aliases=('heart pop', 'double-tap like', 'like animation', 'favorite burst'),
    definition='Tapping a hollow heart squeezes it, then it springs back filled with colour while a '
               'ring and a spray of tiny dots and hearts shoot out around it and fade.',
    phrasings=('make the heart pop and fill in when someone likes it',
               'a like button that explodes into little hearts',
               'when you tap the heart it turns red with a burst of confetti'),
    related=('shape-burst', 'circle-pop', 'confetti-burst', 'heart-wipe', 'pulse-loader', 'badge-count-bump'),
    api=('videobuilder.capabilities.ui.like_heart_burst.like_heart_burst',
         'videobuilder.capabilities.ui.like_heart_burst.heart',
         'videobuilder.capabilities.ui.like_heart_burst.heart_points'),
    demo=lambda: demo.film(draw),
)
