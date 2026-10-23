"""Shape Fill Sweep: an outlined shape floods with colour from one edge to
the opposite one, the filled part growing behind a straight front."""
import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

DIRECTIONS = ('right', 'left', 'down', 'up')


def _path(cv, points):
    c = cv.ctx
    c.new_path()
    c.move_to(*points[0])
    for p in points[1:]:
        c.line_to(*p)
    c.close_path()


def fill_sweep(cv, points, p, color, base=None, edge=None, edge_width=3, direction='right', alpha=1.0):
    """Draw the closed polygon `points` filled `color` up to progress `p`
    (0 -> 1), sweeping in from the edge opposite `direction` ('right' fills
    left to right; also 'left', 'down', 'up'). `base` fills the whole shape
    first (the empty state); `edge` strokes its outline on top, `edge_width`
    px wide. Returns the Box of the shape."""
    if direction not in DIRECTIONS:
        raise ValueError(f'direction must be one of {", ".join(DIRECTIONS)}, not {direction!r}')
    xs, ys = [x for x, _ in points], [y for _, y in points]
    box = vb.Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
    c = cv.ctx
    if base is not None:
        _path(cv, points)
        c.set_source_rgba(*vb.rgba(base, alpha))
        c.fill()
    p = vb.clamp01(p)
    if p > 0:
        x, y, w, h = box
        rect = {'right': (x, y, w * p, h), 'left': (x + w * (1 - p), y, w * p, h),
                'down': (x, y, w, h * p), 'up': (x, y + h * (1 - p), w, h * p)}[direction]
        c.save()
        _path(cv, points)
        c.clip()
        cv.rect(*rect, color, alpha=alpha)
        c.restore()
    if edge is not None:
        _path(cv, points)
        c.set_source_rgba(*vb.rgba(edge, alpha))
        c.set_line_width(edge_width)
        c.set_line_join(cairo.LINE_JOIN_ROUND)
        c.stroke()
    return box


def arrow(cx, cy, w=560, h=300, shaft=0.5, head=0.36):
    """A right-pointing block arrow centred at (cx, cy) as a point list:
    `shaft` is the shaft's height and `head` the head's length, as fractions."""
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
    neck, sh = x1 - w * head, h * shaft / 2
    return [(x0, cy - sh), (neck, cy - sh), (neck, y0), (x1, cy), (neck, y1), (neck, cy + sh), (x0, cy + sh)]


def draw(n, cv):
    pts = arrow(demo.W / 2, demo.H / 2)
    # A steady, progress-bar sweep over nearly the whole clip, so the poster
    # (70%) catches the front mid-shape with the arrow's head still unfilled.
    p = demo.phase(n, 0.4, 2.9)
    box = fill_sweep(cv, pts, p, demo.ACCENT, base='#1f2530', edge=demo.INK, edge_width=4)
    cv.mark('shape', *box)


CAPABILITY = Capability(
    id='shape-fill-sweep',
    name='Shape fill sweep',
    family='shapes',
    group='Explainer & infographic',
    aliases=('color fill wipe', 'progressive fill', 'fill-in transition'),
    definition='An empty outlined shape floods with colour from one side to the other, '
               'the colour advancing behind a straight edge until the whole shape is solid.',
    phrasings=('the arrow fills up with colour from left to right',
               'colour the shape in gradually like a progress bar',
               'make the icon fill in from the bottom up'),
    related=('area-fill-sweep', 'fill-sweep-button', 'outline-to-fill', 'karaoke-highlight-sweep',
             'choropleth-fill', 'icon-line-to-fill'),
    api=('videobuilder.capabilities.shapes.shape_fill_sweep.fill_sweep',
         'videobuilder.capabilities.shapes.shape_fill_sweep.arrow'),
    demo=lambda: demo.film(draw),
)
