"""Icon Line-to-Fill: an icon's outline traces itself on, then its inside
swells from the centre until the line icon has become the solid one -- the
"selected" state of a tab-bar icon, played as a beat."""
import math

import videobuilder as vb
from videobuilder import paths

from .. import _demo as demo
from ..schema import Capability


def _centroid(points):
    xs, ys = zip(*points)
    return sum(xs) / len(xs), sum(ys) / len(ys)


def _trace(ctx, points):
    ctx.new_path()
    ctx.move_to(*points[0])
    for p in points[1:]:
        ctx.line_to(*p)
    ctx.close_path()


def draw_line_to_fill(cv, points, p, color, width=10, fill=None, split=0.55, pop=0.08):
    """Draw the closed icon outline `points` at progress `p` (0 -> 1). Until
    `split` the stroke draws on from `points[0]`; after it the inside fills,
    a copy of the shape growing from its centre, clipped to the outline, and
    the whole icon gives a small `pop` of overshoot as it lands. `fill`
    defaults to `color`."""
    p = vb.clamp01(p)
    line = vb.ease_in_out_quart(vb.clamp01(p / split)) if split > 0 else 1.0
    grow = vb.clamp01((p - split) / (1 - split)) if split < 1 else 1.0
    cx, cy = _centroid(points)
    s = 1 + pop * math.sin(math.pi * grow) * (1 - grow)
    pts = [(cx + (x - cx) * s, cy + (y - cy) * s) for x, y in points]
    if grow > 0:
        k = vb.ease_out_expo(grow)
        c = cv.ctx
        c.save()
        _trace(c, pts)
        c.clip()
        paths.draw(cv, [(cx + (x - cx) * k, cy + (y - cy) * k) for x, y in pts], fill or color, fill=True)
        c.restore()
    if line > 0:
        paths.draw(cv, paths.reveal(pts, line, closed=True), color, width=width)


def heart(cx, cy, size, n=160):
    """A heart outline centred near (cx, cy), about `size` px wide, starting at its top dip."""
    out = []
    for i in range(n):
        t = math.pi * 2 * i / n
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        out.append((cx + x * size / 34, cy - y * size / 34))
    return out[n // 2:] + out[:n // 2]


def star(cx, cy, r, points=5, inner=0.45):
    """A star outline centred at (cx, cy), outer radius `r`, starting at its top point."""
    return [(cx + math.sin(math.pi * i / points) * r * (1 if i % 2 == 0 else inner),
             cy - math.cos(math.pi * i / points) * r * (1 if i % 2 == 0 else inner))
            for i in range(points * 2)]


def house(cx, cy, size):
    """A house outline (roof and walls) centred at (cx, cy), about `size` px wide."""
    h = size / 2
    return [(cx, cy - h), (cx + h, cy - h * 0.05), (cx + h * 0.72, cy - h * 0.05), (cx + h * 0.72, cy + h),
            (cx - h * 0.72, cy + h), (cx - h * 0.72, cy - h * 0.05), (cx - h, cy - h * 0.05)]


ICONS = (house(demo.W / 2 - 260, demo.H / 2, 160),
         heart(demo.W / 2, demo.H / 2 + 6, 175),
         star(demo.W / 2 + 260, demo.H / 2 + 6, 95))
COLORS = (demo.TEAL, demo.ACCENT, demo.TEAL)


def draw(n, cv):
    for i, (pts, color) in enumerate(zip(ICONS, COLORS)):
        t0 = 0.3 + 0.25 * i
        draw_line_to_fill(cv, pts, demo.phase(n, t0, t0 + 1.8), color, width=7)
        xs, ys = zip(*pts)
        cv.mark(f'icon{i}', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


CAPABILITY = Capability(
    id='icon-line-to-fill',
    name='Icon line-to-fill',
    family='shapes',
    group='Icon animation',
    aliases=('outline to solid icon', 'stroke to fill icon', 'icon fill state'),
    definition='An icon first appears as a thin outline drawing itself on, then its inside floods solid '
               'so the line version becomes the filled version.',
    phrasings=('the icon draws as a line and then fills in',
               'outline icons that turn solid when they are selected',
               'trace the heart and then fill it with colour'),
    related=('outline-to-fill', 'line-draw-logo-reveal', 'stroke-draw-logo-loader', 'bookmark-fill',
             'stroke-draw-on', 'shape-fill-sweep'),
    api=('videobuilder.capabilities.shapes.icon_line_to_fill.draw_line_to_fill',
         'videobuilder.paths.reveal'),
    demo=lambda: demo.film(draw),
)
