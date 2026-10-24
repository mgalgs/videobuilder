"""Tracking shot: the camera travels with a moving subject, so the subject
stays put in frame while the world streams past behind (and in front of) it.
The world is a stack of `parallax.Layer`s; this module only works out the
camera's pan from where the subject is, and draws back layers, subject, then
front layers."""
import math

from videobuilder import parallax, paths

from .. import _demo as demo
from ..schema import Capability


def tracking_camera(subject_x, screen_x, start=None):
    """The camera pan (for `parallax.draw`) that holds a subject at world x
    `subject_x` on frame x `screen_x`. With `start`, the camera waits parked at
    that pan until the subject reaches its mark, then picks it up and follows."""
    cam = subject_x - screen_x
    return cam if start is None else max(start, cam)


def tracking_shot(cv, layers, subject_x, screen_x, subject, front=(), start=None):
    """Draw one frame of a tracking shot: `layers` (far first) panned by the
    camera, then `subject(cv, x)` at its frame x, then `front` layers that
    pass in front of it. `subject_x` is the subject's world position this
    frame; see `tracking_camera` for `screen_x` and `start`. Returns the pan."""
    cam = tracking_camera(subject_x, screen_x, start)
    parallax.draw(cv, layers, cam)
    subject(cv, subject_x - cam)
    parallax.draw(cv, front, cam)
    return cam


# -- demo: a ball rolls in, the camera locks on, and the street runs past it --

GROUND = demo.H * 0.68
SPEED = 520            # px per second, world
BALL_R = 40
_SKYLINE = parallax.ridge(480, 70, seed=4)
_BLOCKS = ((0, 60, 150), (75, 45, 105), (135, 70, 190), (225, 50, 125), (290, 80, 165), (390, 55, 140))


def _hills(cv, x):
    pts = [(x + px, GROUND - 150 + py) for px, py in _SKYLINE]
    paths.draw(cv, pts + [(x + 480, GROUND), (x, GROUND)], '#23262f', fill=True)


def _city(cv, x):
    for bx, bw, bh in _BLOCKS:
        cv.rect(x + bx, GROUND - bh, bw, bh, '#3a3f66')
        for wy in range(int(GROUND - bh + 14), int(GROUND - 14), 22):  # lit windows
            cv.rect(x + bx + 10, wy, bw - 20, 6, '#6b74c9', alpha=0.55)


def _road(cv, x):
    cv.rect(x, GROUND, 160, demo.H - GROUND, '#1c1d23')
    cv.rect(x + 20, GROUND + 70, 80, 5, demo.MUTED, alpha=0.7)


def _posts(cv, x):
    cv.rect(x + 40, GROUND - 260, 12, 260 + 160, '#0c0d10')


BACK = (parallax.Layer(0.15, 480, _hills), parallax.Layer(0.45, 480, _city), parallax.Layer(1.0, 160, _road))
FRONT = (parallax.Layer(1.6, 600, _posts),)


def _ball(spin):
    def draw(cv, x):
        y = GROUND + 45 - BALL_R
        cv.shadow(x - BALL_R, GROUND + 40, 2 * BALL_R, 8, radius=4, blur=10, color=(0, 0, 0, 0.6))
        demo.dot(cv, x, y, BALL_R, demo.ACCENT)
        for k in range(2):  # a cross on the ball, so it visibly rolls
            a = spin + k * math.pi / 2
            dx, dy = math.cos(a) * BALL_R * 0.8, math.sin(a) * BALL_R * 0.8
            cv.line(x - dx, y - dy, x + dx, y + dy, demo.INK, width=4)
    return draw


def draw(n, cv):
    t = n / demo.FPS
    sx = 120 + SPEED * t
    tracking_shot(cv, BACK, sx, demo.W / 2, _ball(sx / BALL_R), front=FRONT, start=0)


CAPABILITY = Capability(
    id='tracking-shot',
    name='Tracking shot',
    family='camera',
    group='Camera moves',
    aliases=('follow tracking', 'travelling shot', 'follow shot', 'chase cam', 'trailing camera'),
    definition='The camera travels alongside a moving subject at its pace, keeping it fixed in frame '
               'while the scenery slides by behind it.',
    phrasings=('have the camera follow the ball as it rolls along',
               'keep the character centred while the background scrolls past',
               'move with the subject so only the world behind it moves'),
    related=('zoom-through', 'accumulation-motion-blur', 'motion-blur', 'follow-through',
             'reverse-motion-cut', 'player-movement-trail'),
    api=('videobuilder.capabilities.camera.tracking_shot.tracking_shot',
         'videobuilder.capabilities.camera.tracking_shot.tracking_camera',
         'videobuilder.parallax.draw'),
    demo=lambda: demo.film(draw),
)
