"""Optical zoom: the lens changes focal length while the camera stays put, so
the whole picture grows (or shrinks) about the lens axis as one flat image --
near and far things keep their places relative to each other, with none of
the parallax a camera move would add."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def optical_zoom_scale(p, start_mm=24.0, end_mm=70.0):
    """How much larger the picture draws at progress `p` (0 -> 1) of a zoom
    from `start_mm` to `end_mm`, relative to the `start_mm` framing. Image
    size goes with focal length, and the focal length runs in log space so the
    zoom feels even throughout; `end_mm < start_mm` zooms out."""
    return vb.log_lerp(start_mm, end_mm, vb.clamp01(p)) / start_mm


def focal_length(p, start_mm=24.0, end_mm=70.0):
    """The focal length, in mm, at progress `p` of the same zoom (for a lens readout)."""
    return vb.log_lerp(start_mm, end_mm, vb.clamp01(p))


def optical_zoom(cv, draw, p, start_mm=24.0, end_mm=70.0, center=None):
    """Draw `draw(cv)` (the scene as framed at `start_mm`) through a lens
    zooming to `end_mm`, at progress `p` (0 -> 1). Everything in the scene,
    foreground and background alike, scales by `optical_zoom_scale` about
    `center` (default the frame centre, the lens axis): the camera never moves,
    so the perspective inside the picture never changes. Ease `p` yourself.

    In a film: `optical_zoom(cv, lambda c: street(c, n), vb.ease_in_out_quart(shot.f / shot_frames))`."""
    cx, cy = center if center is not None else (cv.width / 2, cv.height / 2)
    s = optical_zoom_scale(p, start_mm, end_mm)
    with cv.layer(dx=cx * (1 - s), dy=cy * (1 - s), scale=s):
        draw(cv)


# ---- demo: a fixed-camera set with depth (floor, back posts, a gate, a ball on a plinth), lens 24 -> 70 mm ----
_VX, _VY = demo.W / 2, demo.H * 0.44     # vanishing point, just above the lens axis
_GROUND = demo.H * 0.60                  # horizon-to-floor line where the back wall meets the floor
_GATE = '#7b86e0'


def _toward(x, y, t):
    """The point a fraction `t` of the way from (x, y) to the vanishing point."""
    return x + (_VX - x) * t, y + (_VY - y) * t


def _set(cv):
    cv.fill(demo.BG)
    # floor: rails running away to the vanishing point, cross lines bunching up with distance
    for k in range(-8, 9):
        x = demo.W / 2 + k * 160
        cv.line(x, demo.H, *_toward(x, demo.H, 0.72), demo.LINE, width=2)
    for i in range(1, 8):
        y = _GROUND + (demo.H - _GROUND) * (i / 7) ** 1.8
        cv.line(0, y, demo.W, y, demo.LINE, width=2)
    # back wall: a rail and a row of posts, far away so drawn small and dim
    cv.rect(0, _GROUND - 92, demo.W, 8, '#30333c')
    for x in (70, 210, 360, demo.W / 2 - 14, demo.W - 374, demo.W - 224, demo.W - 84):
        cv.rect(x, _GROUND - 140, 28, 140, '#30333c', radius=3)
    # the gate, midway in depth
    gx, gw, top = demo.W / 2 - 150, 300, _GROUND - 150
    cv.rect(gx, top, 22, 232, _GATE, radius=2)
    cv.rect(gx + gw - 22, top, 22, 232, _GATE, radius=2)
    cv.rect(gx - 8, top - 16, gw + 16, 20, _GATE, radius=2)
    cv.rect(gx + 14, top + 4, gw - 28, 6, '#5d67b8')
    # the subject in front: a ball on a plinth
    cv.shadow(demo.W / 2 - 62, _GROUND + 6, 124, 64, radius=4, dy=8, blur=18, color=(0, 0, 0, 0.5))
    cv.rect(demo.W / 2 - 62, _GROUND + 6, 124, 64, '#3a3e48', radius=4)
    cv.rect(demo.W / 2 - 62, _GROUND + 6, 124, 10, '#4a4f5b', radius=4)
    demo.dot(cv, demo.W / 2, _GROUND - 30, r=38, color='#f2b632')
    demo.dot(cv, demo.W / 2 - 12, _GROUND - 42, r=12, color='#ffe08a', alpha=0.6)
    cv.mark('subject', demo.W / 2 - 38, _GROUND - 68, 76, 76)


def _viewfinder(cv, mm, p):
    """The camera's overlay, which does not zoom: corner marks, a centre cross,
    and the focal length with a bar showing how far along the lens range it is."""
    m, k, ink = 34, 36, demo.INK
    for x, y, sx, sy in ((m, m, 1, 1), (demo.W - m, m, -1, 1), (m, demo.H - m, 1, -1), (demo.W - m, demo.H - m, -1, -1)):
        cv.line(x, y, x + sx * k, y, ink, width=3, alpha=0.8)
        cv.line(x, y, x, y + sy * k, ink, width=3, alpha=0.8)
    cx, cy = demo.W / 2, demo.H / 2
    cv.line(cx - 12, cy, cx + 12, cy, ink, width=2, alpha=0.5)
    cv.line(cx, cy - 12, cx, cy + 12, ink, width=2, alpha=0.5)
    x0, x1, y = demo.W - 250, demo.W - 70, demo.H - 62
    cv.rect(x0 - 16, y - 46, x1 - x0 + 32, 66, '#000000', radius=10, alpha=0.45)
    demo.word(cv, f'{mm:.0f} mm', (x0 + x1) / 2, y - 22, size=26, color=ink, font=demo.mono(26))
    cv.line(x0, y + 4, x1, y + 4, demo.MUTED, width=4, alpha=0.6)
    cv.line(x0, y + 4, x0 + (x1 - x0) * p, y + 4, '#f2b632', width=4)


def _draw(n, cv):
    p = vb.ease_in_out_quart(demo.phase(n, 0.4, 2.6))
    optical_zoom(cv, _set, p)
    _viewfinder(cv, focal_length(p), p)


CAPABILITY = Capability(
    id='optical-zoom',
    name='Optical zoom',
    family='camera',
    group='Camera moves',
    aliases=('lens zoom', 'focal length change', 'zoom in', 'zoom out'),
    definition='The camera holds its spot while its lens tightens or widens, so the whole picture '
               'grows or shrinks evenly toward its centre without the depth in it shifting at all.',
    phrasings=('zoom the lens in on the subject without moving the camera',
               'go from a wide shot to a tight shot just by zooming',
               'slowly zoom in from where the camera stands'),
    related=('focus-breathing', 'dolly-zoom', 'zoom-to-detail-magnifier', 'canvas-pan-and-zoom',
             'ui-walkthrough-camera-zoom', 'infinite-zoom-tunnel'),
    api=('videobuilder.capabilities.camera.optical_zoom.optical_zoom',
         'videobuilder.capabilities.camera.optical_zoom.optical_zoom_scale',
         'videobuilder.capabilities.camera.optical_zoom.focal_length'),
    demo=lambda: demo.film(_draw),
)
