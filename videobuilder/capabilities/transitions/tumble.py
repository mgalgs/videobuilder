"""Tumble: the outgoing scene tips backwards on its bottom edge, like a board
falling flat, and drops away in perspective to uncover the incoming scene."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def tumble(cv, a, b, p, focal=2.0, shade=0.55, ease=lambda t: t * t):
    """Draw the tumble at progress `p` (0 -> 1): `b(cv)` underneath, and on
    top `a(cv)` hinged on the frame's bottom edge, rotated back from upright
    (p = 0) to flat (p = 1) and drawn in perspective, so its top edge
    narrows and sinks toward the hinge as it falls. `focal` is the camera's
    distance in frame heights (smaller is a stronger perspective), `shade`
    how dark the falling scene gets as it turns away from the light, and
    `ease` shapes the fall (the default speeds up, as if under gravity).

    In a film, call it while two shots are live in an overlap, e.g.
    `tumble(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    b(cv)
    theta = math.pi / 2 * vb.clamp01(ease(vb.clamp01(p)))
    if theta >= math.pi / 2 - 1e-3:
        return
    w, h = cv.width, cv.height
    off = vb.Canvas(w, h, scale=cv.scale, format=cv.format)
    a(off)
    off.surface.flush()
    f = focal * h
    cx, cy = w / 2, h / 2

    def project(y):
        """Screen (y, horizontal scale) of the scene's row `y` once tipped."""
        d = h - y                      # distance from the hinge
        s = f / (f + d * math.sin(theta))
        return cy + (h - d * math.cos(theta) - cy) * s, s

    top = project(0)[0]
    strips = max(8, min(400, round((h - top) * cv.scale / 2)))
    c = cv.ctx
    seam = 1.0 / cv.scale              # each strip overlaps the next by a device pixel, hiding seams
    for i in range(strips):
        y0, y1 = h * i / strips, h * (i + 1) / strips
        sy0, s0 = project(y0)
        sy1, s1 = project(y1)
        c.save()
        c.move_to(cx - w * s0 / 2, sy0)
        c.line_to(cx + w * s0 / 2, sy0)
        c.line_to(cx + w * s1 / 2, sy1 + seam)
        c.line_to(cx - w * s1 / 2, sy1 + seam)
        c.close_path()
        c.clip()
        c.translate(cx, sy0)
        c.scale((s0 + s1) / 2, (sy1 - sy0) / (y1 - y0))
        c.translate(-cx, -y0)
        c.scale(1 / cv.scale, 1 / cv.scale)
        c.set_source_surface(off.surface, 0, 0)
        c.paint()
        c.restore()
    dark = shade * math.sin(theta)
    if dark > 0:
        s0, s1 = project(0)[1], project(h)[1]
        c.move_to(cx - w * s0 / 2, top)
        c.line_to(cx + w * s0 / 2, top)
        c.line_to(cx + w * s1 / 2, h)
        c.line_to(cx - w * s1 / 2, h)
        c.close_path()
        c.set_source_rgba(0, 0, 0, dark)
        c.fill()


TECHNIQUE = Technique(
    id='tumble',
    name='Tumble',
    family='transitions',
    group='Rotation and 3D',
    aliases=('tumble over', 'tip over'),
    definition='The current scene leans back on its bottom edge like a toppling board and falls flat '
               'into the distance, uncovering the next scene behind it.',
    phrasings=('have the first scene fall over backwards to show the next one',
               'tip the shot over like a panel falling flat',
               'the old scene topples away in 3D and the new one is behind it'),
    related=('roll-up', 'corner-wipe', 'push', 'zoom-out-reveal', 'star-wipe', 'tile-flip'),
    api=('videobuilder.techniques.transitions.tumble.tumble',),
    demo=lambda: demo.two_scenes(tumble, start=0.7, length=1.6),
)
