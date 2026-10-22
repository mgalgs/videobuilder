"""Tilt: the camera stays where it is and pivots up or down, so a scene that
never moves sweeps vertically through the frame."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

SWING = vb.bezier(0.45, 0.0, 0.4, 1.0)   # a hand on the pan bar: eases off, glides, eases to a stop


def tilt_offset(angle, focal):
    """How far, in px, a camera of focal length `focal` px tilted `angle`
    degrees up (negative: down) has lifted its view: `focal * tan(angle)`.
    Equal steps of angle cover more ground the further the camera tips."""
    return focal * math.tan(math.radians(angle))


def tilt(cv, world, p, start=0.0, end=30.0, focal=None, ease=SWING):
    """Draw `world(cv, top, bottom)` seen by a camera tilting from `start` to
    `end` degrees (up is positive) at progress `p` (0 -> 1), eased by `ease`.
    `world` draws in world px: at 0 degrees the frame shows y = 0 .. height,
    and what lies above it has negative y. `top` and `bottom` are the world
    rows in view, so it can skip what is off screen. `focal` defaults to 1.2
    frame heights (a normal lens). Returns the tilt angle now.

    In a film, call it from a shot's draw with `p` from the shot's clock, e.g.
    `tilt(cv, city, vb.clamp01(f / 60), end=40)` to look up a building over two seconds."""
    focal = focal if focal is not None else 1.2 * cv.height
    angle = start + (end - start) * ease(vb.clamp01(p))
    lift = tilt_offset(angle, focal)
    with cv.clip(0, 0, cv.width, cv.height), cv.layer(dy=lift):
        world(cv, -lift, cv.height - lift)
    return angle


# ---- the demo: looking up a signal mast from its base to the beacon on top ----

W, H = demo.W, demo.H
END = 50.0
GROUND = 410
TOP = -500      # the beacon: centred in the frame once the tilt ends
STARS = [(110, -60), (260, -380), (380, -150), (640, -420), (720, -90), (850, -300), (170, -250),
         (560, -20), (900, 40), (60, 140), (300, 60), (800, 180), (470, -470), (680, 250),
         (90, -560), (330, -700), (610, -640), (880, -520), (200, -760), (760, -730)]


def _world(cv, top, bottom):
    cv.fill(demo.BG)
    for y in range(math.floor(top / 90) * 90, int(bottom) + 90, 90):   # faint rows to read the sweep by
        if y < GROUND:
            cv.line(0, y, W, y, demo.LINE, width=1)
    for x, y in STARS:
        demo.dot(cv, x, y, r=3, color=demo.MUTED, alpha=0.8)
    cv.rect(0, GROUND, W, H, '#1c1d23')
    for i, y in enumerate((GROUND + 18, GROUND + 42, GROUND + 76)):
        cv.line(0, y, W, y, demo.LINE, width=2 + i)
    demo.floor(cv, GROUND, demo.MUTED)
    mx = W / 2
    cv.rect(mx - 7, TOP, 14, GROUND - TOP, demo.TEAL)
    for y in range(TOP + 70, GROUND - 60, 110):
        cv.line(mx - 46, y, mx + 46, y, demo.TEAL, width=6)
        cv.line(mx - 46, y, mx + 46, y + 110, demo.TEAL, width=2, alpha=0.6)
        cv.line(mx + 46, y, mx - 46, y + 110, demo.TEAL, width=2, alpha=0.6)
    demo.card(cv, mx, GROUND - 62, w=240, h=124)
    cv.sector(mx, TOP, 70, 0, 2 * math.pi, demo.ACCENT, alpha=0.18)
    demo.dot(cv, mx, TOP, r=30)


def _viewfinder(cv, angle):
    m, k = 36, 44
    for x, y, sx, sy in ((m, m, 1, 1), (W - m, m, -1, 1), (m, H - m, 1, -1), (W - m, H - m, -1, -1)):
        cv.line(x, y, x + sx * k, y, demo.INK, width=3, alpha=0.8)
        cv.line(x, y, x, y + sy * k, demo.INK, width=3, alpha=0.8)
    cv.line(W / 2 - 14, H / 2, W / 2 + 14, H / 2, demo.INK, width=2, alpha=0.5)
    cv.line(W / 2, H / 2 - 14, W / 2, H / 2 + 14, demo.INK, width=2, alpha=0.5)
    gx, g0, g1 = W - 70, H - 110, 110   # the angle gauge: 0 degrees at the bottom, END at the top
    cv.line(gx, g0, gx, g1, demo.MUTED, width=2)
    for d in range(0, int(END) + 1, 10):
        y = g0 + (g1 - g0) * d / END
        cv.line(gx - 10, y, gx, y, demo.MUTED, width=2)
    y = g0 + (g1 - g0) * angle / END
    cv.sector(gx + 14, y, 8, 0, 2 * math.pi, demo.ACCENT)
    f = demo.mono(22, 600)
    vb.text.draw(cv, [f'TILT {angle:4.1f}\N{DEGREE SIGN}'], f, 58, H - 82, demo.INK)


def _demo():
    def draw(n, cv):
        angle = tilt(cv, _world, demo.phase(n, 0.4, 2.6), end=END)
        _viewfinder(cv, angle)
    return demo.film(draw)


CAPABILITY = Capability(
    id='tilt',
    name='Tilt',
    family='camera',
    group='Camera moves',
    aliases=('vertical pan', 'tilt shot', 'tilt up', 'tilt down'),
    definition='The camera keeps its place but pivots to look higher or lower, so the still scene '
               'glides down or up through the frame.',
    phrasings=('slowly look up from the base of the tower to the top',
               'point the camera down from the sky to the street',
               'swing the view upward without moving the camera'),
    related=('tilt-shift-miniature', 'three-d-tilt-on-hover', 'spin', 'focus-breathing',
             'canvas-pan-and-zoom', 'flip'),
    api=('videobuilder.capabilities.camera.tilt.tilt', 'videobuilder.capabilities.camera.tilt.tilt_offset'),
    demo=_demo,
)
