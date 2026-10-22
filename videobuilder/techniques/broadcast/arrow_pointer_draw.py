"""Arrow pointer draw: a hand-drawn arrow strokes itself on along a curve from
a note to a detail, and only once the shaft arrives do its two barbs flick out
to point at the target."""
import math

import videobuilder as vb
from videobuilder import paths

from .. import _demo as demo
from ..schema import Technique


def pointer_arrow_path(start, end, bend=0.35, wave=0.0, steps=64):
    """A point list for an annotation arrow from `start` to `end` ((x, y)
    pairs): a cubic curve bowed sideways by `bend` times the distance (the
    sign picks the side) and, with `wave`, given an S-swing like a quick pen
    stroke."""
    (x0, y0), (x3, y3) = start, end
    dx, dy = x3 - x0, y3 - y0
    nx, ny = dy, -dx  # left-hand normal, scaled by the distance
    x1 = x0 + dx / 3 + nx * (bend + wave)
    y1 = y0 + dy / 3 + ny * (bend + wave)
    x2 = x0 + dx * 2 / 3 + nx * (bend - wave)
    y2 = y0 + dy * 2 / 3 + ny * (bend - wave)
    out = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        out.append((u ** 3 * x0 + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t ** 3 * x3,
                    u ** 3 * y0 + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t ** 3 * y3))
    return out


def draw_pointer_arrow(cv, points, progress, color=demo.INK, width=6, head=30, spread=32, head_share=0.2,
                       hand=1.5, seed=7, alpha=1.0):
    """Draw the arrow along `points` at `progress` (0 -> 1): the shaft grows
    from the first point over the first `1 - head_share` of it, then the two
    barbs (`head` px long, `spread` degrees off the shaft) stroke out from the
    tip over the rest. `hand` px of seeded jitter gives it a marker feel (0:
    clean). Returns the tip's (x, y) once the shaft has started, else None."""
    progress = vb.clamp01(progress)
    if progress <= 0 or len(points) < 2:
        return None
    pts = paths.jitter(points, seed=seed, amount=hand, wander=0.25) if hand else list(points)
    shaft = paths.reveal(pts, vb.clamp01(progress / (1 - head_share)) if head_share < 1 else 1.0)
    if len(shaft) < 2:
        return None
    paths.draw(cv, shaft, color, width=width, alpha=alpha)
    barbs = vb.clamp01((progress - (1 - head_share)) / head_share) if head_share > 0 else 1.0
    tx, ty = pts[-1]
    if barbs > 0:
        # aim the head along the last stretch of the path, not just its last hop
        bx, by = paths.reveal(pts, 1 - min(1.0, head / (paths.length(pts) or 1.0)))[-1]
        angle = math.atan2(ty - by, tx - bx)
        reach = head * vb.ease_out_quint(barbs)
        for side in (-1, 1):
            a = angle + math.pi - side * math.radians(spread)
            paths.draw(cv, [(tx, ty), (tx + math.cos(a) * reach, ty + math.sin(a) * reach)], color,
                       width=width, alpha=alpha)
    return shaft[-1]


# The demo: a row of three plain cards, a note at top left, and a long arrow
# swept from the note to the right-hand card, which nudges up when the head lands.
NOTE = (210, 110)
CARDS = (190, 480, 770)
ROW = 370
_ARROW = pointer_arrow_path((NOTE[0] + 20, NOTE[1] + 50), (CARDS[2] - 132, ROW - 82), bend=0.02, wave=0.2)


def draw(n, cv):
    p = demo.phase(n, 0.35, 2.0)
    p = p * p * (3 - 2 * p)
    lift = 14 * math.sin(math.pi * demo.phase(n, 2.0, 2.4))
    for x in CARDS[:2]:
        demo.card(cv, x, ROW, w=220, h=130, color=demo.LINE)
    demo.card(cv, CARDS[2], ROW - lift, w=220, h=130, color=demo.ACCENT)
    demo.word(cv, 'This one', NOTE[0], NOTE[1], size=44, alpha=demo.phase(n, 0.0, 0.3))
    tip = draw_pointer_arrow(cv, _ARROW, p)
    if tip:
        cv.mark('tip', tip[0] - 8, tip[1] - 8, 16, 16)


TECHNIQUE = Technique(
    id='arrow-pointer-draw',
    name='Arrow pointer draw',
    family='broadcast',
    group='Annotation',
    aliases=('hand-drawn arrow', 'arrow annotation', 'explainer arrow draw', 'callout arrow draw',
             'pointing arrow draw-on', 'annotation arrow'),
    definition='A curved arrow draws itself across the frame toward one detail, its pointed head '
               'snapping on at the end of the stroke to show exactly where to look.',
    phrasings=('draw an arrow on screen pointing at this part',
               'have a sketchy arrow swoop in from the label to the thing it means',
               'animate a pointer arrow that writes itself on and lands on the button'),
    related=('arrow-slide', 'cursor-path-animation', 'cursor-particle-trail', 'whiteboard-marker-drawing',
             'cursor-follower-dot-and-ring', 'map-route-draw'),
    api=('videobuilder.techniques.broadcast.arrow_pointer_draw.draw_pointer_arrow',
         'videobuilder.techniques.broadcast.arrow_pointer_draw.pointer_arrow_path',
         'videobuilder.paths.reveal'),
    demo=lambda: demo.film(draw),
)
