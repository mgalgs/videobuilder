"""Frame delay echo: the whole moving picture is laid over itself at a few
fixed frame offsets, each older copy fainter, so every frame also shows
where the motion was a moment ago."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ..typography.echo_trail_type import echo_trail


def frame_delay_echo(draw, copies=5, delay=3, falloff=0.55):
    """Wrap a scene `draw(n, cv)` into one that echoes it in time: the scene
    as it was `delay`, `2 * delay`, ... `copies * delay` frames ago is
    composited under the live frame, copy `k` at opacity `falloff ** k`.
    Each copy is a whole frame, so draw the scene on a clear canvas (the film's
    `background` behind it) and keep `cv.mark` calls out of it. Frames before
    0 are drawn as frame 0, so the echoes start stacked on the subject."""
    def echoed(n, cv):
        def copy(cv, m, k, alpha):
            with cv.layer(opacity=alpha):
                draw(max(0, m), cv)
        echo_trail(cv, copy, n, copies=copies, lag=delay, falloff=falloff)
    return echoed


PW, PH = 200, 134
START, END = 0.2, 2.6


def _pose(n):
    """Centre and tilt of the photo at frame `n`: a looping swoop that comes
    to rest at the middle of the frame."""
    p = 0.5 - 0.5 * math.cos(math.pi * demo.phase(n, START, END))
    a = p * 2 * math.pi
    cx = demo.W / 2 + 250 * math.sin(a)
    cy = demo.H / 2 - 95 * math.sin(2 * a)
    return cx, cy, 0.22 * math.sin(a)


def _scene(n, cv):
    cx, cy, tilt = _pose(n)
    img = demo.photo()
    c = cv.ctx
    c.save()
    c.translate(cx, cy)
    c.rotate(tilt)
    cv.image(img, *vb.Box(-PW / 2, -PH / 2, PW, PH).cover(img.w, img.h))
    cv.outline(-PW / 2, -PH / 2, PW, PH, demo.INK, width=2, alpha=0.9)
    c.restore()


_echoed = frame_delay_echo(_scene, copies=6, delay=3, falloff=0.62)


def draw(n, cv):
    _echoed(n, cv)
    cx, cy, _ = _pose(n)
    cv.mark('photo', cx - PW / 2, cy - PH / 2, PW, PH)


CAPABILITY = Capability(
    id='frame-delay-echo',
    name='Frame delay echo',
    family='vfx',
    group='Recursion & feedback',
    aliases=('time echo', 'delayed echo', 'frame echo', 'echo trail', 'ghost trail', 'motion echo',
             'afterimage trail'),
    definition='Fainter copies of the picture from a few frames back are stacked under the live one, '
               'so a moving subject drags a fading replay of its recent path.',
    phrasings=('make the clip leave ghost copies of itself a few frames behind',
               'an afterimage effect where the motion repeats faintly just after it happens',
               'stack delayed see-through copies of the shot for a trailing echo'),
    related=('echo-trail-type', 'delay', 'scatter-time-playback', 'linear-repeater-stagger', 'multiples',
             'smear-frame'),
    api=('videobuilder.capabilities.vfx.frame_delay_echo.frame_delay_echo',
         'videobuilder.capabilities.typography.echo_trail_type.echo_trail'),
    demo=lambda: demo.film(draw),
)
