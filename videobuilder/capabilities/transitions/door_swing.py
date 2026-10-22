"""Door Swing: the outgoing scene turns on a hinge down one side edge, in
perspective, like a door swinging open away from the viewer, and the
incoming scene is there behind it."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def door_swing(cv, a, b, p, hinge='left', angle=90.0, focal=1.5, strips=64, shade=0.55,
               ease=vb.bezier(0.5, 0, 0.3, 1)):
    """Draw the swing at progress `p` (0 -> 1): `b(cv)` underneath, and
    `a(cv)` on top as a panel turning about its `hinge` edge ('left' or
    'right') from flat to `angle` degrees away from the viewer. `focal` is the
    camera distance in frame widths (smaller: stronger perspective); the
    panel darkens by up to `shade` as it turns away from the light, and casts
    a soft shadow on `b`.

    Cairo has no perspective transform, so the panel is drawn as `strips`
    vertical slices, each placed with its own affine scale.

    In a film, call it while two shots are live in an overlap, e.g.
    `door_swing(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    b(cv)
    t = ease(vb.clamp01(p))
    if t >= 1 and angle >= 90:
        return
    w, h = cv.width, cv.height
    cy = h / 2
    th = math.radians(angle) * t
    f = focal * w
    sub = vb.Canvas(w, h, scale=cv.scale, format=cv.format)
    a(sub)
    sub.surface.flush()
    side = 1 if hinge == 'left' else -1
    x_hinge = 0 if hinge == 'left' else w

    def project(u):
        """(screen x, size factor) of the panel point `u` px from the hinge."""
        s = f / (f + u * math.sin(th))
        return x_hinge + side * u * math.cos(th) * s, s

    c = cv.ctx
    # a soft shadow round the panel's footprint, so it lifts off the incoming scene
    xe, se = project(w)
    reach = abs(xe - x_hinge)
    if reach > 1:
        with cv.layer(opacity=0.6 * math.sin(math.pi * min(1.0, 2 * t))):
            sx = x_hinge if side > 0 else xe
            cv.shadow(sx, cy - cy * se, reach, h * se, blur=50, spread=6, color=(0, 0, 0, 0.7))
    dark = shade * (1 - math.cos(th))
    for i in range(strips):
        u0, u1 = w * i / strips, w * (i + 1) / strips
        (x0, s0), (x1, s1) = project(u0), project(u1)
        if abs(x1 - x0) < 1e-3:
            continue
        sm = (s0 + s1) / 2
        c.save()
        # the slice's true trapezoid, overlapping the next by a device pixel so slices don't seam
        x1e = x1 + side / cv.scale
        c.move_to(x0, cy - cy * s0)
        c.line_to(x1e, cy - cy * s1)
        c.line_to(x1e, cy + cy * s1)
        c.line_to(x0, cy + cy * s0)
        c.close_path()
        c.clip()
        c.save()
        c.translate(x0, cy)
        c.scale((x1 - x0) / (u1 - u0) * side, sm)
        c.translate(-(u0 if side > 0 else w - u0), -cy)
        c.scale(1 / sub.scale, 1 / sub.scale)
        c.set_source_surface(sub.surface, 0, 0)
        c.get_source().set_filter(cairo.FILTER_GOOD)
        c.paint()
        c.restore()
        if dark > 0:
            c.set_source_rgba(0, 0, 0, dark * (0.8 + 0.2 * i / strips))
            c.paint()
        c.restore()


CAPABILITY = Capability(
    id='door-swing',
    name='Door swing',
    family='transitions',
    group='Rotation and 3D',
    aliases=('door open', 'hinge transition', 'swing door', 'door wipe'),
    definition='The current shot pivots on one side edge and swings out towards the camera in 3D, '
               'like a door being pulled open, revealing the next shot behind it.',
    phrasings=('open the first scene like a door to get to the next one',
               'swing the old shot away on a hinge at the left edge',
               'make the slide turn on its side like a door opening'),
    related=('pendulum-swing', 'uncover', 'push', 'roll-up', 'zoom-out-reveal', 'curtain-reveal'),
    api=('videobuilder.capabilities.transitions.door_swing.door_swing',),
    demo=lambda: demo.two_scenes(door_swing, start=0.7, length=1.6),
)
