"""Roll-up: the outgoing scene curls into a cylinder at its bottom edge and
the roll travels up the frame, winding the picture away and leaving the
incoming scene behind it."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


STANDARD = vb.ease.bezier(0.4, 0.0, 0.2, 1.0)  # easing in, settling as it leaves the top


def roll_up(cv, a, b, p, radius=0.07, grow=0.05, strips=48, shadow=0.55, ease=STANDARD):
    """Draw the roll-up at progress `p` (0 -> 1): `b(cv)` underneath, `a(cv)`
    flat above a roll that starts sitting on the bottom edge and climbs until
    it has left the top. The roll's face shows the last stretch of `a` it wound up,
    squeezed and shaded round the curve, and it casts a soft shadow on `b`.

    `radius` is the bare roll's radius as a share of the frame height;
    `grow` is how much thicker it gets by the end, as more of the picture is
    wound on. `strips` slices the curved face (more is smoother). `ease`
    shapes the roll's travel.

    In a film, call it while two shots are live in an overlap, e.g.
    `roll_up(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    w, h = cv.width, cv.height
    e = ease(vb.clamp01(p))
    r0, r_end = h * radius, h * (radius + grow)
    yc = (h + r0) - e * (h + r0 + r_end)            # roll centre: touching the bottom -> off the top
    rolled = max(0.0, h - yc)
    r = r0 + h * grow * math.sqrt(rolled / h) if rolled else r0
    b(cv)
    if yc - r >= h:
        a(cv)
        return
    # the shadow the roll throws down on the uncovered scene
    c = cv.ctx
    c.save()
    g = cairo.LinearGradient(0, yc, 0, yc + r * 2.2)
    g.add_color_stop_rgba(0, 0, 0, 0, shadow)
    g.add_color_stop_rgba(1, 0, 0, 0, 0)
    c.rectangle(0, yc, w, r * 2.2)
    c.set_source(g)
    c.fill()
    c.restore()
    # the part of `a` still lying flat
    if yc > 0:
        with cv.clip(0, 0, w, yc):
            a(cv)
    # the roll's face: rows of `a` just past the fold, wrapped round the cylinder
    src = vb.Canvas(w, h, scale=cv.scale, format=cv.format)
    a(src)
    src.surface.flush()
    span = math.pi * r                               # paper length across the visible half-turn
    for i in range(strips):
        t0, t1 = -math.pi / 2 + math.pi * i / strips, -math.pi / 2 + math.pi * (i + 1) / strips
        y0, y1 = yc + r * math.sin(t0), yc + r * math.sin(t1)
        s0 = yc + span * (1 - (i / strips))          # top of the face shows the freshest-wound rows
        s1 = yc + span * (1 - ((i + 1) / strips))
        if y1 <= 0 or y0 >= h or y1 - y0 < 0.05:
            continue
        c.save()
        c.rectangle(0, y0, w, y1 - y0 + 0.6)
        c.clip()
        c.translate(0, y0)
        c.scale(1, (y1 - y0) / (s1 - s0))
        c.translate(0, -s0)
        c.scale(1 / cv.scale, 1 / cv.scale)
        c.set_source_surface(src.surface, 0, 0)
        c.get_source().set_extend(cairo.EXTEND_PAD)
        c.paint()
        c.restore()
    # light from above: bright on the upper shoulder, dark underneath
    c.save()
    g = cairo.LinearGradient(0, yc - r, 0, yc + r)
    g.add_color_stop_rgba(0.0, 0, 0, 0, 0.45)
    g.add_color_stop_rgba(0.18, 1, 1, 1, 0.10)
    g.add_color_stop_rgba(0.32, 1, 1, 1, 0.28)
    g.add_color_stop_rgba(0.55, 0, 0, 0, 0.05)
    g.add_color_stop_rgba(1.0, 0, 0, 0, 0.70)
    c.rectangle(0, yc - r, w, 2 * r)
    c.set_source(g)
    c.fill()
    c.restore()


CAPABILITY = Capability(
    id='roll-up',
    name='Roll-up',
    family='transitions',
    group='Page and Fold',
    aliases=('scroll roll', 'roller reveal', 'roll away'),
    definition='The old scene winds itself into a tube starting at the bottom edge, and the tube climbs '
               'up and off the frame, leaving the new scene where the picture used to lie.',
    phrasings=('roll the first shot up like a window blind to show the next one',
               'make the scene curl up from the bottom like a rolled poster',
               'wind the picture away upward and reveal what is underneath'),
    related=('uncover', 'corner-wipe', 'push', 'zoom-out-reveal', 'tumble', 'slide-over-cover'),
    api=('videobuilder.capabilities.transitions.roll_up.roll_up',),
    demo=lambda: demo.two_scenes(roll_up, start=1.6, length=1.2),
)
