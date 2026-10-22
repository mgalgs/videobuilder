"""Push-in: the camera creeps forward toward the subject, so the subject
slowly fills more of the frame and the things around it, further back, grow
less and drift outward -- a move through depth, not a flat scale."""
import math

from .. import _demo as demo
from ..schema import Technique


def push_in_scale(z, p, travel=0.4):
    """How much larger a plane `z` away from the starting camera draws at
    progress `p` (0 -> 1) of a push-in that moves the camera `travel` forward
    (same units as `z`). A plane at `z` draws at `z / (z - travel * p)`, so
    near planes grow faster than far ones. `p` is used as given: ease it first."""
    return z / max(1e-6, z - travel * p)


def push_in_point(x, y, z, p, travel=0.4, center=(demo.W / 2, demo.H / 2)):
    """Where the point (x, y) of plane `z`, as it looked from the starting
    camera, lands at progress `p` of the same push-in (for floors and rails
    that run in depth between planes)."""
    s = push_in_scale(z, p, travel)
    cx, cy = center
    return cx + (x - cx) * s, cy + (y - cy) * s


def push_in(cv, planes, p, travel=0.4, center=(demo.W / 2, demo.H / 2)):
    """Draw a push-in at progress `p` (0 -> 1). `planes` is a list of
    `(z, draw)`: `draw(cv)` paints that plane in frame coordinates as the
    starting camera sees it, and `z` (> `travel`) is its distance from that
    camera. Planes draw far to near, each scaled about `center` by
    `push_in_scale`. A single plane at z = 1 is a plain slow zoom of
    1 / (1 - travel); several planes give the parallax of a real dolly.

    In a film, drive `p` with a slow ease across the whole shot:
    `push_in(cv, [(3, room), (1, hero)], vb.ease_in_out_quart(shot.f / shot_frames), travel=0.3)`."""
    cx, cy = center
    for z, draw in sorted(planes, key=lambda pl: -pl[0]):
        s = push_in_scale(z, p, travel)
        with cv.layer(dx=cx * (1 - s), dy=cy * (1 - s), scale=s):
            draw(cv)


# ---- demo: a dot on a gridded floor between pillars, the camera creeping in ----
_TRAVEL = 0.55
_EYE = 330                                   # camera height above the floor, px at z = 1
_DOT_Z = 1.25
_PILLARS = [(x, z) for z in (1.5, 2.3, 3.4, 5.0) for x in (-1, 1)]
_COLUMNS = (-1500, -1000, -500, 0, 500, 1000, 1500)  # floor rails, px at z = 1
_ROWS = [0.75 + 0.35 * k * 1.25 ** k for k in range(14)]


def _start_view(X, Y, z):
    """A world point (X, Y px at z = 1, measured from the frame centre) as the
    starting camera sees it."""
    return demo.W / 2 + X / z, demo.H / 2 + Y / z


def _pillar(x, z):
    def draw(cv):
        px, top = _start_view(x * 560, -420, z)
        _, bottom = _start_view(0, _EYE, z)
        w = 60 / z
        cv.rect(px - w / 2, top, w, bottom - top, '#2a3140', alpha=0.95)
        cv.outline(px - w / 2, top, w, bottom - top, '#3c4658', width=2 / z ** 0.5)
    return draw


def _dot(cv):
    cx, cy = _start_view(0, -10, _DOT_Z)
    _, floor = _start_view(0, _EYE, _DOT_Z)
    w = 120 / _DOT_Z
    cv.shadow(cx - w / 2, floor - 6, w, 12, radius=6, blur=18, color=(0, 0, 0, 0.6))
    demo.dot(cv, cx, cy, r=70 / _DOT_Z)


def _floor(cv, p):
    near = _TRAVEL * p + 0.12                 # never draw behind the camera
    far = _ROWS[-1]
    pt = lambda X, z: push_in_point(*_start_view(X, _EYE, z), z, p, _TRAVEL)  # noqa: E731
    for X in _COLUMNS:
        cv.line(*pt(X, max(near, 0.3)), *pt(X, far), demo.LINE, width=2)
    for z in _ROWS:
        if z > near:
            cv.line(*pt(-4000, z), *pt(4000, z), demo.LINE, width=2, alpha=min(1.0, 2.4 / z))


def _draw(n, cv):
    t = demo.phase(n, 0.2, 2.9)
    p = 0.5 - 0.5 * math.cos(math.pi * t)     # slow at both ends
    _floor(cv, p)
    planes = [(z, _pillar(x, z)) for x, z in _PILLARS] + [(_DOT_Z, _dot)]
    push_in(cv, planes, p, _TRAVEL)


TECHNIQUE = Technique(
    id='push-in',
    name='Push-in',
    family='camera',
    group='Camera moves',
    aliases=('slow push', 'dolly in', 'digital dolly', 'slow zoom in', 'creep in'),
    definition='The camera glides steadily forward toward the subject, which grows to fill more of the frame '
               'while the things around it, further back, swell less and slide outward.',
    phrasings=('slowly move the camera in on the subject',
               'creep closer to it over the shot so it gets bigger',
               'a gentle dolly forward that tightens the framing'),
    related=('zoom-through', 'push', 'roll-up', 'dolly-zoom', 'ui-walkthrough-camera-zoom', 'zoom-out-reveal'),
    api=('videobuilder.techniques.camera.push_in.push_in',
         'videobuilder.techniques.camera.push_in.push_in_scale',
         'videobuilder.techniques.camera.push_in.push_in_point'),
    demo=lambda: demo.film(_draw),
)
