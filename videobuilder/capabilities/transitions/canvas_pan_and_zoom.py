"""Canvas pan and zoom: both scenes sit on one big canvas, apart from each
other; the camera pulls back to show the stretch between them, glides
across, and settles in on the second."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def camera(p, offset, out=0.4):
    """The camera at progress `p` (0 -> 1) flying from a frame to the frame
    `offset` (dx, dy) canvas px away: `(x, y, scale)`, how far along the
    way it has panned and its zoom. The pan eases in and out; the zoom dips to `out` at the midpoint, evenly in log
    space, and is back at 1 at both ends."""
    e = vb.ease_in_out_quart(p)
    dip = math.sin(math.pi * vb.clamp01(p)) ** 2
    return offset[0] * e, offset[1] * e, vb.log_lerp(1.0, out, dip)


def canvas_pan_and_zoom(cv, a, b, p, offset=None, out=0.4, backdrop=None, ground='#101114'):
    """Draw the move at progress `p` (0 -> 1). `a(cv)` and `b(cv)` each draw
    a full frame; they are placed on a shared canvas, `a` at the origin and
    `b` at `offset` (dx, dy) canvas px (default 1.6 frames right and 0.7
    down), each clipped to its own frame. `backdrop(cv, x0, y0, x1, y1)`
    draws the canvas under them in canvas px, given the part in view (a
    grid, the lines joining the regions); without one the canvas is plain
    `ground`. At p = 0 and 1 the picture is exactly `a` and `b`.

    In a film, call it while two shots are live in an overlap, e.g.
    `canvas_pan_and_zoom(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    w, h = cv.width, cv.height
    dx, dy = offset if offset is not None else (1.6 * w, 0.7 * h)
    x, y, s = camera(p, (dx, dy), out)
    cx, cy = w / 2 + x, h / 2 + y
    with cv.layer(dx=w / 2 - cx * s, dy=h / 2 - cy * s, scale=s):
        if backdrop is None:
            cv.fill(ground)
        else:
            backdrop(cv, cx - w / 2 / s, cy - h / 2 / s, cx + w / 2 / s, cy + h / 2 / s)
        for scene, ox, oy in ((a, 0, 0), (b, dx, dy)):
            with cv.layer(dx=ox, dy=oy), cv.clip(0, 0, w, h):
                scene(cv)


# ---- the demo: a node graph on a gridded board ----

OFFSET = (1.6 * demo.W, 0.7 * demo.H)
RING = (demo.W * 0.4, demo.H * 0.5)
DIAMOND = (demo.W * 1.25, demo.H * 0.15)
BARS = (OFFSET[0] + demo.W * 0.5, OFFSET[1] + demo.H * 0.5)


def _cubic(p0, p1, p2, p3, n=48):
    pts = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        pts.append(tuple(u ** 3 * a + 3 * u * u * t * b + 3 * u * t * t * c + t ** 3 * d
                         for a, b, c, d in zip(p0, p1, p2, p3)))
    return pts


def _board(cv, x0, y0, x1, y1, step=90):
    cv.fill(demo.BG)
    for i in range(math.floor(x0 / step), math.ceil(x1 / step) + 1):
        cv.line(i * step, y0, i * step, y1, demo.LINE, width=2)
    for j in range(math.floor(y0 / step), math.ceil(y1 / step) + 1):
        cv.line(x0, j * step, x1, j * step, demo.LINE, width=2)
    r, (dx, dy), (bx, by) = 170, DIAMOND, BARS
    vb.paths.draw(cv, _cubic((RING[0] + r, RING[1]), (RING[0] + 500, RING[1]), (dx - 420, dy), (dx - 150, dy)),
                  demo.TEAL, width=6)
    vb.paths.draw(cv, _cubic((dx + 150, dy), (dx + 700, dy), (bx, dy + 200), (bx, by - 220)), demo.TEAL, width=6)
    d = 150
    vb.paths.draw(cv, [(dx, dy - d), (dx + d, dy), (dx, dy + d), (dx - d, dy)], '#f2b705', fill=True)


def _ring(cv):
    cv.arc(*RING, 150, 0, 2 * math.pi, demo.TEAL, width=40)


def _bars(cv):
    x, y = demo.W / 2, demo.H / 2
    for i, (bw, color) in enumerate(((560, demo.INK), (460, demo.TEAL), (360, demo.INK))):
        cv.rect(x - 280, y - 170 + i * 130, bw, 80, color, radius=40)


def _demo():
    def draw(n, cv):
        canvas_pan_and_zoom(cv, _ring, _bars, demo.phase(n, 0.5, 2.5), offset=OFFSET, backdrop=_board)
    return demo.film(draw)


TECHNIQUE = Technique(
    id='canvas-pan-and-zoom',
    name='Canvas pan and zoom',
    family='transitions',
    group='Slides and Pushes',
    aliases=('canvas zoom navigation', 'spatial zoom', 'zoomable canvas'),
    definition='The camera backs away from one spot on a large board, travels across it and closes in '
               'on another spot, so the next scene is a different place on the same surface.',
    phrasings=('fly across a big whiteboard from one section to the next',
               'zoom out, slide over to the next part of the map, then zoom back in',
               'move between slides like they are all laid out on one huge canvas'),
    related=('ui-walkthrough-camera-zoom', 'infinite-zoom-tunnel', 'zoom-to-location-map',
             'zoom-through-shape', 'zoom-through', 'ken-burns-effect'),
    api=('videobuilder.techniques.transitions.canvas_pan_and_zoom.canvas_pan_and_zoom',
         'videobuilder.techniques.transitions.canvas_pan_and_zoom.camera'),
    demo=_demo,
)
