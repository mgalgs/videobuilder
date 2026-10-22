"""Zoom-through shape: a stack of nested outlines grows out of the centre,
each one swelling past the edges of the frame in turn, so the eye seems to
fly through one shape after another."""
import math

from ...looks import kit as looks
from .. import _demo as demo
from ..schema import Technique


def polygon(cx, cy, r, sides=4, turn=0.0):
    """The corners of a regular polygon centred at (cx, cy) with corner
    radius `r`, turned `turn` radians (0 puts a corner straight up)."""
    return [(cx + r * math.sin(turn + 2 * math.pi * k / sides),
             cy - r * math.cos(turn + 2 * math.pi * k / sides)) for k in range(sides)]


def zoom_through_shape(cv, cx, cy, travel, sides=4, colors=('#ffffff',), ratio=1.6, smallest=6.0,
                       reach=None, width=0.03, turn=0.0, twist=0.0, alpha=1.0):
    """Draw nested `sides`-gon outlines about (cx, cy), `travel` shapes deep.

    Rings sit on a geometric ladder, each `ratio` times the one inside it,
    and every unit of `travel` grows them all by one rung: the outermost ring
    leaves the frame as a new one appears at the centre, so whole-number
    `travel` values look the same and any speed loops seamlessly. Animate
    `travel` (e.g. `2.5 * eased_progress`) to fly through that many shapes.

    `colors` cycle ring by ring and stay with their ring as it grows. Strokes
    are `width` times the ring's radius, so near rings are thick and far ones
    hairline; rings fade in from `smallest` px. `reach` is where rings stop
    (default: the frame's corner from the centre, plus a stroke). `turn` sets
    the shapes' angle; `twist` adds that many radians per rung, for a spiral."""
    reach = reach or math.hypot(max(cx, cv.width - cx), max(cy, cv.height - cy)) * 1.15
    whole = math.floor(travel)
    frac = travel - whole
    rungs = math.ceil(math.log(reach / smallest) / math.log(ratio)) + 1
    for i in range(rungs, -1, -1):  # outermost first
        r = smallest * ratio ** (i + frac)
        if r > reach * ratio:
            continue
        ring = i - whole  # a ring's identity: fixed as it grows, so its colour does too
        fade = min(1.0, math.log(r / smallest) / math.log(ratio))  # newest ring fades up
        pts = polygon(cx, cy, r, sides, turn + twist * ring)
        looks.outline(cv, pts, colors[ring % len(colors)], max(1.0, r * width), alpha=alpha * fade)


def draw(n, cv):
    p = demo.phase(n, 0.0, demo.SECONDS)
    travel = 3.0 * p ** 1.4  # eases into the flight, three shapes deep
    zoom_through_shape(cv, demo.W / 2, demo.H / 2, travel, sides=4, colors=(demo.INK, demo.ACCENT),
                       width=0.035)
    cv.mark('tunnel', demo.W / 2 - 40, demo.H / 2 - 40, 80, 80)


TECHNIQUE = Technique(
    id='zoom-through-shape',
    name='Zoom-through shape',
    family='shapes',
    group='Geometric motion',
    aliases=('tunnel zoom', 'shape portal', 'infinite zoom shapes'),
    definition='Outlines of the same shape sit one inside another and keep growing out of the centre, '
               'so it feels like flying forward through each frame in turn.',
    phrasings=('fly through a tunnel of squares',
               'nested shapes that keep zooming toward the camera',
               'a portal of outlines we pass straight through'),
    related=('infinite-zoom-tunnel', 'scale-zoom-through', 'canvas-pan-and-zoom', 'zoom-through',
             'mandelbrot-zoom', 'cross-zoom'),
    api=('videobuilder.techniques.shapes.zoom_through_shape.zoom_through_shape',
         'videobuilder.techniques.shapes.zoom_through_shape.polygon',
         'videobuilder.looks.kit.outline'),
    demo=lambda: demo.film(draw),
)
