"""Dolly zoom: the camera travels along its axis while the lens zooms the
other way, so the subject holds its size and everything behind it stretches
away or crowds in."""
from .. import _demo as demo
from ..schema import Technique
from ...ease import ease_in_out_quart, log_lerp


def dolly_zoom_scale(z, p, near=0.5, far=3.0):
    """How large a plane `z` behind the subject draws at progress `p` (0 -> 1)
    of a dolly zoom, relative to its size on the subject's plane (z = 0).

    The camera's distance to the subject runs from `near` to `far` (in the
    same units as `z`) while the zoom keeps the subject at scale 1, so a plane
    at `z` draws at `d / (d + z)`. `near < far` pulls back and flattens the
    background; swap them to push in and make the background rush away."""
    d = log_lerp(near, far, p)
    return d / (d + z)


def dolly_zoom_point(x, y, z, p, near=0.5, far=3.0, center=(demo.W / 2, demo.H / 2)):
    """Where the point (x, y) on plane `z` lands in the frame at progress `p`,
    seen through the same dolly zoom as `dolly_zoom` (for floors, rails and
    other lines that run in depth between planes)."""
    s = dolly_zoom_scale(z, p, near, far)
    cx, cy = center
    return cx + (x - cx) * s, cy + (y - cy) * s


def dolly_zoom(cv, planes, p, near=0.5, far=3.0, center=(demo.W / 2, demo.H / 2)):
    """Draw a dolly zoom at progress `p` (0 -> 1). `planes` is a list of
    `(z, draw)`: `draw(cv)` paints that plane in frame coordinates as it would
    look standing on the subject's plane, and `z` (>= 0) is how far behind the
    subject it stands. Planes draw far to near, each scaled about `center` by
    `dolly_zoom_scale`; the subject itself is the plane at z = 0 and never
    changes size.

    In a film, drive `p` across the shot: `dolly_zoom(cv, [(4, room), (0, hero)], shot.f / shot_frames)`."""
    cx, cy = center
    for z, draw in sorted(planes, key=lambda pl: -pl[0]):
        s = dolly_zoom_scale(z, p, near, far)
        with cv.layer(dx=cx * (1 - s), dy=cy * (1 - s), scale=s):
            draw(cv)


# ---- demo: a corridor of frames around a held dot ----
_FRAME_W, _FRAME_H = 1240, 700          # each frame as it would look on the subject's plane
_FLOOR = demo.H / 2 + _FRAME_H / 2      # the corridor's floor, on the subject's plane
_DEPTHS = [0.12 * k ** 1.35 for k in range(1, 15)]
_RAILS = (-1.0, -0.5, 0.0, 0.5, 1.0)


def _frame(z):
    def draw(cv):
        x0, y0 = demo.W / 2 - _FRAME_W / 2, demo.H / 2 - _FRAME_H / 2
        width = 9
        fade = max(0.25, 1 - z / 4)
        cv.line(x0, _FLOOR, x0 + _FRAME_W, _FLOOR, demo.LINE, width=4, alpha=fade)
        for x0_, y0_, x1_, y1_ in ((x0, _FLOOR, x0, y0), (x0, y0, x0 + _FRAME_W, y0),
                                   (x0 + _FRAME_W, y0, x0 + _FRAME_W, _FLOOR)):
            cv.line(x0_, y0_, x1_, y1_, demo.TEAL, width=width, alpha=fade)
    return draw


def _draw(n, cv):
    p = ease_in_out_quart(demo.phase(n, 0.4, 2.7))
    far = _DEPTHS[-1]
    for r in _RAILS:
        x = demo.W / 2 + r * _FRAME_W / 2
        cv.line(*dolly_zoom_point(x, _FLOOR, 0, p), *dolly_zoom_point(x, _FLOOR, far, p), demo.LINE, width=3)
    dolly_zoom(cv, [(z, _frame(z)) for z in _DEPTHS], p)
    demo.dot(cv, demo.W / 2, demo.H / 2 + 40, r=90)


TECHNIQUE = Technique(
    id='dolly-zoom',
    name='Dolly zoom',
    family='transitions',
    group='Zoom',
    aliases=('vertigo zoom', 'vertigo effect', 'Hitchcock zoom', 'contra-zoom', 'trombone shot'),
    definition='The subject in the middle stays exactly the same size while the space behind it '
               'seems to stretch away or squeeze up close, as if the camera moved one way and zoomed the other.',
    phrasings=('keep the subject still but make the background warp and pull away behind it',
               'that dizzy shot where the room stretches but the person stays the same size',
               'push in and zoom out at the same time'),
    related=('optical-zoom', 'push-in', 'infinite-zoom-tunnel', 'zoom-to-location-map',
             'zoom-to-detail-magnifier', 'canvas-pan-and-zoom'),
    api=('videobuilder.techniques.transitions.dolly_zoom.dolly_zoom',
         'videobuilder.techniques.transitions.dolly_zoom.dolly_zoom_scale',
         'videobuilder.techniques.transitions.dolly_zoom.dolly_zoom_point'),
    demo=lambda: demo.film(_draw),
)
