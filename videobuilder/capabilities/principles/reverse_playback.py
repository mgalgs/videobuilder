"""Reverse Playback: a move plays forward, then the same frames run backwards
so everything retraces its path to where it began -- a rewind."""
import math

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Capability
from .bounce_ease_out import bounce_ease_out


def rewind_frame(n, turn, hold=0, speed=1.0):
    """The source frame to show at frame `n` when playback runs forward up to
    frame `turn`, holds there `hold` frames, then plays backwards at `speed`
    times normal speed, stopping on frame 0."""
    if n <= turn:
        return n
    back = max(0.0, n - turn - hold) * speed
    return max(0, round(turn - back))


def reverse_playback(draw, turn, hold=0, speed=1.0):
    """Wrap a film's `draw(n, cv)` so it plays forward to frame `turn`, holds
    `hold` frames, then rewinds to frame 0 at `speed` (see `rewind_frame`).

    In a film: `vb.Film(draw=reverse_playback(draw, turn=45, hold=6), ...)`,
    or call `draw(rewind_frame(n, ...), cv)` for one layer inside a shot."""
    return lambda n, cv: draw(rewind_frame(n, turn, hold, speed), cv)


GROUND = demo.H - 170
R = 46
X0, X1 = 260, demo.W - 260
TURN, HOLD = round(1.3 * demo.FPS), round(0.2 * demo.FPS)


def scene(n, cv):
    """The forward move: a ball tossed in from the left, bouncing to rest on the right."""
    p = demo.phase(n, 0.1, 1.3)
    x = X0 + (X1 - X0) * vb.ease_out_quint(p)
    top, rest = 150 + R, GROUND - R
    y = top + (rest - top) * bounce_ease_out(p)
    demo.floor(cv, GROUND)
    demo.dot(cv, x, y, R)
    spin = (x - X0) / R  # rolling: one radian per radius travelled
    demo.dot(cv, x + 0.55 * R * math.cos(spin - math.pi / 2), y + 0.55 * R * math.sin(spin - math.pi / 2),
             9, color=demo.BG)
    cv.mark('ball', x - R, y - R, 2 * R, 2 * R)


def _triangle(cv, x, y, s, left, color):
    c = cv.ctx
    d = -s if left else s
    c.new_path()
    c.move_to(x - d / 2, y - s / 2)
    c.line_to(x + d / 2, y)
    c.line_to(x - d / 2, y + s / 2)
    c.close_path()
    c.set_source_rgba(*rgba(color))
    c.fill()


def _transport(cv, n, src):
    """The deck around the scene: a play / rewind badge and a scrub bar whose
    playhead follows the source frame, so the reversal reads at a glance."""
    rewinding = n > TURN + HOLD and src > 0
    color = demo.ACCENT if rewinding else demo.TEAL
    x, y = 80, 70
    if rewinding:
        _triangle(cv, x + 14, y, 28, True, color)
        _triangle(cv, x + 40, y, 28, True, color)
        demo.word(cv, 'REWIND', x + 150, y, size=34, color=color)
    elif n <= TURN:
        _triangle(cv, x + 20, y, 30, False, color)
        demo.word(cv, 'PLAY', x + 112, y, size=34, color=color)
    bx, bw, by = 80, demo.W - 160, demo.H - 70
    cv.rect(bx, by - 3, bw, 6, demo.LINE, radius=3)
    head = bx + bw * src / TURN
    cv.rect(bx, by - 3, head - bx, 6, color, radius=3)
    demo.dot(cv, head, by, 11, color=color)


def draw(n, cv):
    src = rewind_frame(n, TURN, HOLD)
    scene(src, cv)
    _transport(cv, n, src)


CAPABILITY = Capability(
    id='reverse-playback',
    name='Reverse Playback',
    family='principles',
    group='Time remapping',
    aliases=('rewind', 'backwards play', 'reverse motion', 'play in reverse'),
    definition='An animation runs forward and then the very same motion plays backwards, '
               'so everything retraces its path and ends where it started.',
    phrasings=('play it forward, then rewind it back to the start',
               'run the animation backwards',
               'make it look like the tape is being rewound'),
    related=('reverse-motion-cut', 'interruptible-motion', 'reverse-cymbal', 'flip', 'layout-animation-flip',
             'frame-by-frame-hand-drawn-animation'),
    api=('videobuilder.capabilities.principles.reverse_playback.reverse_playback',
         'videobuilder.capabilities.principles.reverse_playback.rewind_frame'),
    demo=lambda: demo.film(draw),
)
