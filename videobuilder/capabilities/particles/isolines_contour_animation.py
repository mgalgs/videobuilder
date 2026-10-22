"""Isolines contour animation: the level lines of a smooth scalar field, traced
fresh every frame, so as the field changes the rings swell, pinch, merge and
split like a contour map of moving terrain."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

# Marching-squares edges per corner case. Corners: 0 top-left, 1 top-right,
# 2 bottom-right, 3 bottom-left; edges: 0 top, 1 right, 2 bottom, 3 left.
# Cases 5 and 10 are saddles, resolved by the cell's centre value.
_CASES = {
    1: ((3, 0),), 2: ((0, 1),), 3: ((3, 1),), 4: ((1, 2),), 6: ((0, 2),), 7: ((3, 2),),
    8: ((2, 3),), 9: ((0, 2),), 11: ((1, 2),), 12: ((1, 3),), 13: ((0, 1),), 14: ((3, 0),),
}
_EDGES = ((0, 1), (1, 2), (3, 2), (0, 3))  # corner pairs each edge joins


def sample_field(field, x, y, w, h, cols=160, rows=90):
    """`field(px, py)` sampled on a (cols + 1) x (rows + 1) lattice over the box
    (x, y, w, h), as a list of rows. Pass the result to `isolines` to trace
    several levels from one sampling."""
    return [[field(x + w * i / cols, y + h * j / rows) for i in range(cols + 1)] for j in range(rows + 1)]


def isolines(grid, level, x, y, w, h):
    """The line segments where the sampled `grid` (from `sample_field`) crosses
    `level`, as ((x0, y0), (x1, y1)) pairs in film px over the box (x, y, w, h),
    found by marching squares with linear interpolation along cell edges."""
    rows, cols = len(grid) - 1, len(grid[0]) - 1
    cw, ch = w / cols, h / rows
    out = []
    for j in range(rows):
        top, bot = grid[j], grid[j + 1]
        for i in range(cols):
            v = (top[i], top[i + 1], bot[i + 1], bot[i])
            case = (v[0] > level) | (v[1] > level) << 1 | (v[2] > level) << 2 | (v[3] > level) << 3
            if case in (0, 15):
                continue
            if case in (5, 10):
                high = sum(v) / 4 > level
                pairs = ((3, 0), (1, 2)) if (case == 5) != high else ((0, 1), (2, 3))
            else:
                pairs = _CASES[case]
            px = (x + i * cw, x + (i + 1) * cw, x + (i + 1) * cw, x + i * cw)
            py = (y + j * ch, y + j * ch, y + (j + 1) * ch, y + (j + 1) * ch)

            def point(edge):
                a, b = _EDGES[edge]
                d = v[b] - v[a]
                s = (level - v[a]) / d if d else 0.5
                return px[a] + s * (px[b] - px[a]), py[a] + s * (py[b] - py[a])
            out.extend((point(e0), point(e1)) for e0, e1 in pairs)
    return out


def draw_isolines(cv, field, x, y, w, h, levels, color=demo.MUTED, width=2.0, alpha=1.0,
                  major=None, major_color=demo.ACCENT, major_width=3.0, cols=160, rows=90):
    """Stroke the contour lines of `field(px, py)` over the box (x, y, w, h), one
    per value in `levels`. Every `major`-th level (if given) is drawn in
    `major_color` at `major_width`, like an index contour on a map. Call it every
    frame with a field that depends on the film's time and the lines animate.
    `cols` x `rows` sets the sampling grid: finer is smoother and slower.
    Returns the Box."""
    grid = sample_field(field, x, y, w, h, cols, rows)
    c = cv.ctx
    c.save()
    c.set_line_cap(1)   # round, so segment joints don't show
    for k, level in enumerate(levels):
        segs = isolines(grid, level, x, y, w, h)
        if not segs:
            continue
        is_major = major and k % major == major - 1
        c.new_path()
        for (x0, y0), (x1, y1) in segs:
            c.move_to(x0, y0)
            c.line_to(x1, y1)
        c.set_source_rgba(*vb.rgba(major_color if is_major else color, alpha))
        c.set_line_width(major_width if is_major else width)
        c.stroke()
    c.restore()
    return vb.Box(x, y, w, h)


def blob_field(centers):
    """A field that is a sum of soft round hills, one per (cx, cy, radius, height)
    in `centers`: a ready-made terrain whose contours merge when hills meet."""
    def f(px, py):
        return sum(hgt * math.exp(-((px - cx) ** 2 + (py - cy) ** 2) / (2 * r * r)) for cx, cy, r, hgt in centers)
    return f


def draw(n, cv):
    t = n / demo.FPS
    p = vb.ease_in_out_quart(demo.phase(n, 0.2, 2.6))
    cx, cy = demo.W / 2, demo.H / 2
    gap = 185 * (1 - p) + 52
    tilt = 0.5 * p
    dx, dy = gap * math.cos(tilt), gap * math.sin(tilt)
    wob = 9 * math.sin(t * 2.1)
    field = blob_field(((cx - dx, cy - dy + wob, 78, 1.0), (cx + dx, cy + dy - wob, 78, 1.0),
                        (cx + 330 * math.cos(t * 0.9), cy + 170 * math.sin(t * 1.3), 40, 0.5)))
    m = 20
    box = draw_isolines(cv, field, m, m, demo.W - 2 * m, demo.H - 2 * m,
                        [0.08 + 0.1 * k for k in range(12)], major=4, width=1.4, major_width=2.4)
    cv.mark('contours', *box)


CAPABILITY = Capability(
    id='isolines-contour-animation',
    name='Isolines contour animation',
    family='particles',
    group='Noise & fields',
    aliases=('contour lines', 'level sets', 'topographic lines', 'isolines', 'contour map animation'),
    definition='Thin lines trace equal values of a hidden, changing field, so the rings drift, swell, '
               'pinch together and break apart like a topographic map of shifting ground.',
    phrasings=('animated topographic map lines that move and merge',
               'contour lines like a weather map that keep reshaping',
               'rings of elevation lines flowing around as the hills underneath change'),
    related=('marching-squares-contour', 'animated-gradient-sweep', 'morph-cut', 'pixelate-transition',
             'interlace-combing', 'sparkline-draw'),
    api=('videobuilder.capabilities.particles.isolines_contour_animation.draw_isolines',
         'videobuilder.capabilities.particles.isolines_contour_animation.isolines',
         'videobuilder.capabilities.particles.isolines_contour_animation.sample_field',
         'videobuilder.capabilities.particles.isolines_contour_animation.blob_field'),
    demo=lambda: demo.film(draw),
)
