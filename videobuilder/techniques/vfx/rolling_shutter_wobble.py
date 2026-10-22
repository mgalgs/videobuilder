"""Rolling Shutter Wobble: the frame is read out top to bottom, so each row
sees the scene a moment later than the row above; a fast sideways shake
leans upright things over and bends them like jelly."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def rolling_shutter(cv, scene, t, readout=1 / 30, bands=72, y=0.0, h=None):
    """Draw `scene(cv, t)` -- the whole frame as it looks at time `t` seconds --
    with a rolling shutter: the region from `y` down `h` px (default the whole
    frame) is cut into `bands` horizontal strips, and the strip at fraction
    `f` of the way down is drawn from `scene(cv, t + f * readout)`. Anything
    moving sideways faster than the readout skews; changing speed bends it.
    `readout` 0 is a plain frame. More `bands` means smoother slants."""
    h = cv.height - y if h is None else h
    if readout == 0:
        scene(cv, t)
        return
    snap = lambda v: round(v * cv.scale) / cv.scale  # noqa: E731 -- whole device rows, so bands neither gap nor overlap
    for i in range(bands):
        y0, y1 = snap(y + h * i / bands), snap(y + h * (i + 1) / bands)
        if y1 <= y0:
            continue
        with cv.clip(0, y0, cv.width, y1 - y0):
            scene(cv, t + (i + 0.5) / bands * readout)


def shake(t, amount=110.0, hz=2.6, start=0.5, end=2.6, ramp=0.35):
    """A horizontal camera shake in px at time `t`: a sine of `amount` px at
    `hz`, faded in over `ramp` s from `start` and out by `end`, with a little
    second harmonic so the speed changes and the slant bends, not just leans."""
    k = vb.clamp01((t - start) / ramp) * vb.clamp01((end - t) / ramp)
    w = 2 * math.pi * hz * t
    return amount * k * (math.sin(w) + 0.35 * math.sin(2.3 * w + 1.0))


TOWERS = ((0.08, 0.12, 0.62, demo.TEAL), (0.24, 0.09, 0.44, demo.ACCENT), (0.38, 0.11, 0.70, demo.MUTED),
          (0.54, 0.08, 0.52, demo.TEAL), (0.67, 0.11, 0.64, demo.ACCENT), (0.83, 0.10, 0.46, demo.MUTED))


def skyline(cv, dx):
    """The demo's subject: upright towers with window grids, panned by `dx`."""
    W, H = demo.W, demo.H
    ground = H * 0.86
    cv.fill(demo.BG)
    demo.dot(cv, W * 0.8 + dx * 0.4, H * 0.2, r=H * 0.07, color=demo.INK, alpha=0.85)
    for x, w, h, color in TOWERS:
        x, w, h = x * W + dx, w * W, h * H
        cv.rect(x, ground - h, w, h, color)
        for wy in range(int(ground - h + H * 0.04), int(ground - H * 0.05), int(H * 0.07)):
            for wx in (x + w * 0.2, x + w * 0.6):
                cv.rect(wx, wy, w * 0.2, H * 0.035, demo.BG, alpha=0.55)
    cv.rect(0, ground, W, H - ground, demo.LINE)
    demo.floor(cv, ground)


def draw(n, cv):
    rolling_shutter(cv, lambda c, t: skyline(c, shake(t)), n / demo.FPS, readout=0.12)


TECHNIQUE = Technique(
    id='rolling-shutter-wobble',
    name='Rolling shutter wobble',
    family='vfx',
    group='Time displacement',
    aliases=('jello effect', 'rolling shutter skew', 'shutter skew'),
    definition='When the camera jerks sideways, upright shapes lean and wiggle like jelly, '
               'because the top of the picture is caught a split second before the bottom.',
    phrasings=('make the shot wobble like cheap phone footage being shaken',
               'the buildings bend and lean as the camera whips side to side',
               'give it that jelly smartphone-camera skew'),
    related=('tape-wobble', 'scroll-velocity-skew', 'crane-shot', 'handheld-shake', 'whip-pan', 'swirl'),
    api=('videobuilder.techniques.vfx.rolling_shutter_wobble.rolling_shutter',
         'videobuilder.techniques.vfx.rolling_shutter_wobble.shake'),
    demo=lambda: demo.film(draw),
)
