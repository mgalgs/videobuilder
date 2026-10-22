"""Star Rating Fill: a row of empty star outlines fills with colour from left
to right up to a score, each star giving a small pop as it fills, the last
one filled only part way for a fractional rating."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

GOLD = '#f6b93b'


def star_points(cx, cy, r, inner=0.48, points=5):
    """The outline of a `points`-pointed star centred at (cx, cy), tips at
    radius `r` and notches at `r * inner`, first tip straight up."""
    out = []
    for i in range(points * 2):
        a = -math.pi / 2 + i * math.pi / points
        k = r if i % 2 == 0 else r * inner
        out.append((cx + k * math.cos(a), cy + k * math.sin(a)))
    return out


def draw_star_rating(cv, x, y, rating, p, count=5, size=80, gap=28, color=GOLD, empty=demo.MUTED,
                     pop=0.25, ease=vb.ease_in_out_quart):
    """Draw `count` stars from the top-left (x, y), each `size` px across and
    `gap` apart, filling left to right to `rating` (may be fractional) as `p`
    runs 0 -> 1. The fill sweeps across under `ease` by `1 - pop`; each star
    that fills whole swells and settles over the next `pop` of `p`. Empty
    stars show as `empty` outlines. Returns the Box of the row."""
    sweep = 1 - pop
    level = rating * ease(vb.clamp01(p / sweep)) if sweep > 0 else rating * (p > 0)
    r = size / 2
    c = cv.ctx
    for i in range(count):
        cx, cy = x + r + i * (size + gap), y + r
        amount = vb.clamp01(level - i)
        scale = 1.0
        if pop > 0 and rating >= i + 1:
            # p at which this star became full, from inverting the eased sweep numerically
            done = next((k / 200 * sweep for k in range(201)
                         if rating * ease(k / 200) >= i + 1 - 1e-9), sweep)
            t = vb.clamp01((p - done) / pop)
            scale = 1 + 0.28 * math.sin(math.pi * t) * (1 - t) ** 0.5 if 0 < t < 1 else 1.0
        pts = star_points(0, 0, r * scale)
        c.save()
        c.translate(cx, cy)
        vb.paths.draw(cv, pts, empty, width=max(2, size / 22), closed=True)
        if amount > 0:
            with cv.clip(-r * scale, -r * scale, 2 * r * scale * amount, 2 * r * scale):
                vb.paths.draw(cv, pts, color, fill=True)
        c.restore()
    w = count * size + (count - 1) * gap
    return vb.Box(x, y, w, size)


def draw(n, cv):
    rating, count, size, gap = 4.5, 5, 120, 36
    w = count * size + (count - 1) * gap
    x, y = (demo.W - w) / 2, demo.H / 2 - size / 2 - 40
    p = demo.phase(n, 0.4, 2.6)
    box = draw_star_rating(cv, x, y, rating, p, count=count, size=size, gap=gap)
    cv.mark('stars', *box)
    shown = rating * vb.ease_in_out_quart(vb.clamp01(p / 0.75))
    demo.word(cv, f'{shown:.1f}', demo.W / 2, y + size + 90, size=64, color=demo.INK, weight=700)


CAPABILITY = Capability(
    id='star-rating-fill',
    name='Star rating fill',
    family='ui',
    group='Toggles & controls',
    aliases=('star rating', 'rating stars', 'review stars animation', 'five-star fill'),
    definition='A row of hollow stars fills with colour one after another up to a score, each star '
               'bumping as it completes and the last filled only partly for a half or fractional score.',
    phrasings=('animate the five stars filling in for a 4.5 rating',
               'show the review score as stars lighting up one by one',
               'stars that fill with gold from left to right to the rating'),
    related=('spotlight-hover', 'star-wipe', 'starfield', 'icon-line-to-fill', 'circle-pop', 'border-glow-follow'),
    api=('videobuilder.capabilities.ui.star_rating_fill.draw_star_rating',
         'videobuilder.capabilities.ui.star_rating_fill.star_points'),
    demo=lambda: demo.film(draw),
)
