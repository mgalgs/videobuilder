"""Time Remapping: play a piece of animation at a speed that changes over
time -- normal, then a ramp down into slow motion, then a ramp up past real
time -- by feeding the animation a retimed clock instead of the real one.
videobuilder had no retiming helper, so this module adds one."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def speed_ramp(t, times, speeds):
    """Output time `t` (seconds) -> source time (seconds), for a playback
    speed that runs linearly between keyframes: `speeds[i]` at `times[i]`
    (1 is real time, 0.25 slow motion, 0 a freeze, negative plays backwards).
    The source time is the area under that speed curve from 0 to `t`; before
    `times[0]` and after `times[-1]` the end speeds hold."""
    if len(times) != len(speeds) or len(times) < 2:
        raise ValueError('need matching keyframes, at least two')
    if any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError('keyframe times must increase')
    src = speeds[0] * min(t, times[0])
    for (t0, s0), (t1, s1) in zip(zip(times, speeds), zip(times[1:], speeds[1:])):
        if t <= t0:
            break
        u = min(t, t1) - t0
        s = s0 + (s1 - s0) * u / (t1 - t0)   # speed at the end of the covered part
        src += u * (s0 + s) / 2
    if t > times[-1]:
        src += speeds[-1] * (t - times[-1])
    return src


def speed_at(t, times, speeds):
    """The playback speed `speed_ramp` uses at output time `t`."""
    return vb.ease.interpolate(t, times, speeds)


def remapped(draw, times, speeds, fps):
    """Wrap a film's `draw(n, cv)` so it plays on the `speed_ramp` clock: the
    inner `draw` gets the source frame, a float (round it if it needs whole
    frames)."""
    def retimed(n, cv):
        return draw(speed_ramp(n / fps, times, speeds) * fps, cv)
    return retimed


# The demo: a ball swinging on a steady beat, retimed 1x -> slow motion -> 3x.
TIMES = (0.0, 0.55, 1.05, 1.75, 2.25, 3.0)
SPEEDS = (1.0, 1.0, 0.15, 0.15, 2.5, 2.5)
SWING = 1.4  # seconds per full swing, in source time
TRACK_Y, AMP, R = 220, 300, 24
GRAPH = (180, 330, demo.W - 360, 150)  # x, y, w, h of the speed curve
TOP = 3.0  # speed at the graph's top edge


def _ball_x(src):
    return demo.W / 2 + AMP * math.sin(2 * math.pi * src / SWING)


def _subject(n, cv):
    """The source animation, drawn at source frame `n` (a float)."""
    x = _ball_x(n / demo.FPS)
    demo.dot(cv, x, TRACK_Y, R)
    cv.mark('ball', x - R, TRACK_Y - R, 2 * R, 2 * R)


def _graph(cv, t):
    x, y, w, h = GRAPH
    cv.line(x, y + h, x + w, y + h, demo.LINE, width=2)
    one = y + h - h / TOP
    cv.line(x, one, x + w, one, demo.LINE, width=1, alpha=0.6)
    demo.word(cv, '1x', x - 28, one, size=18, color=demo.MUTED, font=demo.mono(18))
    end = demo.SECONDS
    pts = [(x + w * i / 120, y + h - h * speed_at(end * i / 120, TIMES, SPEEDS) / TOP) for i in range(121)]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        cv.line(ax, ay, bx, by, demo.MUTED, width=3)
    px = x + w * vb.clamp01(t / end)
    py = y + h - h * speed_at(t, TIMES, SPEEDS) / TOP
    cv.line(px, y, px, y + h, demo.TEAL, width=2, alpha=0.7)
    demo.dot(cv, px, py, 7, color=demo.TEAL)


def draw(n, cv):
    t = n / demo.FPS
    demo.floor(cv, TRACK_Y + R + 16, demo.LINE)
    for k in range(6, 0, -1):  # where it was a few output frames back: bunched in slow motion, strung out fast
        src = speed_ramp(t - k / demo.FPS, TIMES, SPEEDS)
        demo.dot(cv, _ball_x(src), TRACK_Y, R, color=demo.ACCENT, alpha=0.08 * (7 - k))
    remapped(_subject, TIMES, SPEEDS, demo.FPS)(n, cv)
    _graph(cv, t)
    s = speed_at(t, TIMES, SPEEDS)
    demo.word(cv, f'{s:.2f}x', demo.W / 2, 80, size=56, color=demo.TEAL if s < 1 else demo.INK,
              font=demo.mono(56))


TECHNIQUE = Technique(
    id='time-remapping',
    name='Time Remapping',
    family='principles',
    group='Time remapping',
    aliases=('speed ramp', 'speed ramping', 'time warp', 'retiming'),
    definition='The playback speed of a motion changes as it runs, gliding from normal pace into '
               'slow motion and then racing faster than real time, without cutting.',
    phrasings=('slow it right down in the middle, then speed it back up',
               'ramp the speed so the action goes into slow-mo and then whips forward',
               'change how fast the animation plays partway through'),
    related=('hyperlapse', 'scatter-time-playback', 'timing', 'distance-based-duration',
             'timecode-counter', 'delay'),
    api=('videobuilder.techniques.principles.time_remapping.speed_ramp',
         'videobuilder.techniques.principles.time_remapping.remapped',
         'videobuilder.techniques.principles.time_remapping.speed_at'),
    demo=lambda: demo.film(draw),
)
