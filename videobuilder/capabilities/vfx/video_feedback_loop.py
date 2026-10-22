"""Video feedback loop: a camera pointed at the screen showing its own picture.
The frame contains a slightly smaller, slightly turned copy of itself, which
contains another, and so on into a spiralling tunnel; anything moving in front
leaves a trail of delayed, colour-drifting echoes down the tunnel."""
import colorsys
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def shift_hue(color, turns):
    """`color` (a hex string or 0-255 rgb tuple) with its hue turned by `turns`
    of the colour wheel, as a 0-255 rgb tuple."""
    r, g, b = vb.canvas.rgba(color)[:3]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return tuple(round(255 * x) for x in colorsys.hsv_to_rgb((h + turns) % 1.0, s, v))


def video_feedback(cv, scene, t, depth=28, zoom=0.88, spin=0.09, center=None, lag=1 / 30,
                   screen=None, fade=0.06, background=demo.BG):
    """Draw a video feedback tunnel at time `t` (seconds) into the whole frame.

    Level 0 is the live picture; level k is the same picture seen k times
    through the loop: scaled by `zoom**k` and turned by `spin * k` radians
    about `center` (frame px, default the middle), drawn as it was at time
    `t - k * lag` (each trip round the loop costs one frame of delay) and
    dimmed by a further `fade` per level towards `background`. `screen` is the box
    (x, y, w, h) where the next level shows (default the whole frame), so a
    bezel or margin repeats down the tunnel. `scene(cv, t, k)` draws the
    picture at time `t` for level `k` in plain frame coordinates; draw the
    background of each level yourself or leave it to the default fill.
    Levels are drawn outermost first, each over its screen box, with the
    level's live content composited over the deeper levels."""
    cx, cy = center if center is not None else (cv.width / 2, cv.height / 2)
    sx, sy, sw, sh = screen if screen is not None else (0, 0, cv.width, cv.height)
    c = cv.ctx

    def level(k):
        if k > depth:
            return
        c.save()
        # Each level only shows through the previous level's screen.
        c.rectangle(sx, sy, sw, sh)
        c.clip()
        cv.fill(background)
        if k < depth:
            c.save()
            c.translate(cx, cy)
            c.rotate(spin)
            c.scale(zoom, zoom)
            c.translate(-cx, -cy)
            level(k + 1)
            c.restore()
        scene(cv, t - k * lag, k)
        if fade > 0 and k:
            cv.fill(background, alpha=fade)
        c.restore()

    c.save()
    c.rectangle(0, 0, cv.width, cv.height)
    c.clip()
    cv.fill(background)
    level(0)
    c.restore()
    return vb.Box(0, 0, cv.width, cv.height)


# ---- demo ----

MARGIN = 70  # the bezel round each nested screen


def _scene(cv, t, k):
    # A bright frame for the "monitor" edge and a dot circling inside it; both drift
    # round the hue wheel the deeper they sit, the way a real loop smears colour.
    x, y, w, h = MARGIN, MARGIN * demo.H / demo.W, demo.W - 2 * MARGIN, demo.H - 2 * MARGIN * demo.H / demo.W
    edge = shift_hue(demo.TEAL, 0.035 * k)
    cv.outline(x, y, w, h, edge, width=14, radius=10)
    if t < 0:
        return
    a = 2.4 * t
    r = 330 * vb.clamp01(t / 0.6)
    demo.dot(cv, demo.W / 2 + r * math.cos(a), demo.H / 2 + 0.6 * r * math.sin(a), r=46,
             color=shift_hue(demo.ACCENT, 0.05 * k))


def draw(n, cv):
    t = n / demo.FPS
    # The camera eases into a tighter twist as the shot runs, so the tunnel visibly winds up.
    p = demo.phase(n, 0.2, 2.6)
    spin = 0.03 + 0.07 * p * p * (3 - 2 * p)
    my = MARGIN * demo.H / demo.W
    box = video_feedback(cv, _scene, t, depth=26, zoom=0.9, spin=spin, lag=2 / demo.FPS,
                         screen=(MARGIN, my, demo.W - 2 * MARGIN, demo.H - 2 * my))
    cv.mark('feedback', *box)


CAPABILITY = Capability(
    id='video-feedback-loop',
    name='Video feedback loop',
    family='vfx',
    group='Recursion & feedback',
    aliases=('video feedback', 'camera-at-monitor feedback', 'infinite tunnel', 'feedback trails',
             'Droste tunnel'),
    definition='The picture holds a smaller, slightly rotated copy of itself, again and again, so the frame '
               'spirals into an endless tunnel where every moving thing leaves a delayed, colour-shifting trail.',
    phrasings=('point the camera at its own screen so it makes an infinite tunnel',
               'a trippy endless spiral of the frame inside itself',
               'make the shot echo into itself with trails like old analogue feedback'),
    related=('seamless-loop', 'follow-cam', 'pulldown-judder', 'hyperlapse', 'rotoscope-look',
             'interruptible-motion'),
    api=('videobuilder.capabilities.vfx.video_feedback_loop.video_feedback',
         'videobuilder.capabilities.vfx.video_feedback_loop.shift_hue'),
    demo=lambda: demo.film(draw),
)
