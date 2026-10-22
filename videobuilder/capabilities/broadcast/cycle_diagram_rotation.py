"""Cycle diagram rotation: labelled stages pop in one by one around a circle,
each joined to the next by a curved arrow that draws itself, and once the
loop closes a marker runs round it, lighting each stage as it passes."""
import math

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Capability


def cycle_angles(count, start=-math.pi / 2):
    """The angles in radians of `count` stages spaced evenly round a circle,
    the first at `start` (default: the top), going clockwise on screen."""
    return [start + i * 2 * math.pi / count for i in range(count)]


def _arrowhead(cv, x, y, heading, size, color, alpha):
    c = cv.ctx
    back, side = heading + math.pi, size * 0.55
    bx, by = x + size * math.cos(back), y + size * math.sin(back)
    nx, ny = -math.sin(heading) * side, math.cos(heading) * side
    c.new_path()
    c.move_to(x, y)
    c.line_to(bx + nx, by + ny)
    c.line_to(bx - nx, by - ny)
    c.close_path()
    c.set_source_rgba(*rgba(color, alpha))
    c.fill()


def draw_cycle_diagram(cv, labels, cx, cy, r, build=1.0, lap=None, node_r=40, font=None,
                       color=demo.TEAL, node_fill=demo.LINE, ink=demo.INK, marker=demo.ACCENT,
                       arrow_width=4, ease=vb.ease_out_back):
    """A cycle diagram of `labels` round a circle of radius `r` about (cx, cy).

    `build` (0 -> 1) reveals it in reading order: stage 1 pops in, the arrow
    from it to stage 2 draws along the circle, stage 2 pops in, and so on,
    the last arrow closing the loop back to stage 1. `lap` places a marker on
    the loop, in turns from stage 1 (0.25 is a quarter of the way round; only
    the fractional part matters), and lights a stage while it passes through
    it; None hides it. `ease` shapes each stage's pop. Returns the stage
    centres."""
    count = len(labels)
    angles = cycle_angles(count)
    font = font or demo.font(round(node_r * 0.42), 800)
    gap = math.asin(min(1.0, (node_r + 10) / r)) * 2  # arrow ends clear of the stage circles
    # Each stage then its outgoing arrow take one slot; the stage pops in the first 40% of its slot.
    slot = vb.clamp01(build) * count
    lit = None
    if lap is not None:
        turn = (lap % 1.0) * 2 * math.pi
        near = [i for i in range(count) if abs(math.remainder(angles[i] - angles[0] - turn, 2 * math.pi)) < gap / 2]
        lit = near[0] if near else None
    for i in range(count):
        a0, a1 = angles[i] + gap / 2, angles[i] + 2 * math.pi / count - gap / 2
        grow = vb.clamp01((slot - i - 0.4) / 0.6)
        if grow > 0:
            tip = a0 + (a1 - a0) * vb.ease_out_quint(grow)
            cv.arc(cx, cy, r, a0, tip, color, width=arrow_width)
            _arrowhead(cv, cx + r * math.cos(tip), cy + r * math.sin(tip), tip + math.pi / 2,
                       arrow_width * 3.4, color, 1.0)
    centres = []
    for i, (label, a) in enumerate(zip(labels, angles)):
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        centres.append((x, y))
        pop = vb.clamp01((slot - i) / 0.4)
        if pop <= 0:
            continue
        s = ease(pop)
        on = i == lit
        demo.dot(cv, x, y, (node_r + 5) * s, marker if on else color)
        demo.dot(cv, x, y, node_r * s, marker if on else node_fill)
        demo.word(cv, label, x, y, font=font, color=ink, alpha=min(1.0, pop * 1.5))
    if lap is not None and lit is None:  # inside a stage, the lit stage stands in for the marker
        a = angles[0] + (lap % 1.0) * 2 * math.pi
        mx, my = cx + r * math.cos(a), cy + r * math.sin(a)
        demo.dot(cv, mx, my, node_r * 0.42, marker, alpha=0.3)
        demo.dot(cv, mx, my, node_r * 0.24, marker)
        demo.dot(cv, mx, my, node_r * 0.1, ink)
    return centres


LABELS = ('Plan', 'Build', 'Test', 'Learn')
R = 175


def draw(n, cv):
    cx, cy = demo.W / 2, demo.H / 2
    build = demo.phase(n, 0.1, 1.5)
    t = demo.phase(n, 1.5, 3.0)
    lap = 0.08 + t if build >= 1 else None  # one full turn, starting just clear of stage 1
    draw_cycle_diagram(cv, LABELS, cx, cy, R, build, lap)
    cv.mark('cycle', cx - R - 45, cy - R - 45, 2 * R + 90, 2 * R + 90)


CAPABILITY = Capability(
    id='cycle-diagram-rotation',
    name='Cycle diagram rotation',
    family='broadcast',
    group='Process diagrams',
    aliases=('cycle diagram', 'circular process loop', 'process cycle', 'loop diagram'),
    definition='Labelled steps appear one after another around a ring, joined by curved arrows that draw '
               'themselves, then a marker circles the finished loop and lights each step it reaches.',
    phrasings=('show our four-step process as a loop with arrows going round',
               'a circular diagram where each stage pops in and a dot travels around it',
               'animate the plan, build, test, learn cycle as a ring of steps'),
    related=('chord-diagram-draw', 'rotating-polygon-loop', 'spinner-ring', 'rotating-circular-text',
             'rotating-rings', 'progress-ring'),
    api=('videobuilder.capabilities.broadcast.cycle_diagram_rotation.draw_cycle_diagram',
         'videobuilder.capabilities.broadcast.cycle_diagram_rotation.cycle_angles'),
    demo=lambda: demo.film(draw),
)
