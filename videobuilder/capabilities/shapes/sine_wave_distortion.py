"""Sine Wave Distortion: every point of a shape is pushed sideways by a sine
of its position along the other axis, and the sine's phase advances with
time, so a ripple runs through the shape while it stays where it is."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def sine_warp(points, t, amplitude=40.0, wavelength=400.0, speed=1.0, axis='y', phase=0.0):
    """`points` displaced by a travelling sine at time `t` seconds.

    `axis='y'` moves each point up/down by `amplitude * sin(2pi (x / wavelength - speed t) + phase)`
    (the wave travels along x, `speed` cycles a second, positive to the right);
    `axis='x'` moves points left/right by the same function of y. Only
    existing points move, so resample a sparse outline first
    (`vb.paths.resample(points, n)`) or straight edges stay straight. Pairs
    with `vb.paths.draw`."""
    if axis not in ('x', 'y'):
        raise ValueError(f"sine_warp: axis must be 'x' or 'y', not {axis!r}")
    k, w = 2 * math.pi / wavelength, 2 * math.pi * speed * t - phase
    if axis == 'y':
        return [(x, y + amplitude * math.sin(k * x - w)) for x, y in points]
    return [(x + amplitude * math.sin(k * y - w), y) for x, y in points]


def _edge(x0, x1, y, n=160):
    return [(x0 + (x1 - x0) * i / (n - 1), y) for i in range(n)]


def draw(n, cv):
    t = n / demo.FPS
    amp = 44 * vb.ease_in_out_quart(demo.phase(n, 0.2, 1.0))  # flat band first, then the wave swells in
    x0, x1, cy, half = 120, demo.W - 120, demo.H / 2, 36
    warp = lambda pts: sine_warp(pts, t, amplitude=amp, wavelength=300, speed=0.6)  # noqa: E731
    top, bottom = _edge(x0, x1, cy - half), _edge(x0, x1, cy + half)
    demo.floor(cv, cy, demo.LINE)  # the undistorted centre line, for reference
    vb.paths.draw(cv, warp(top) + warp(bottom)[::-1], demo.ACCENT, fill=True)
    for dy in (-half / 2, half / 2):
        vb.paths.draw(cv, warp(_edge(x0, x1, cy + dy)), demo.INK, width=2, alpha=0.25)
    vb.paths.draw(cv, warp(_edge(x0, x1, cy)), demo.TEAL, width=4)
    cv.mark('band', x0, cy - half - 44, x1 - x0, 2 * (half + 44))


CAPABILITY = Capability(
    id='sine-wave-distortion',
    name='Sine wave distortion',
    family='shapes',
    group='Waves & ripples',
    aliases=('sine warp', 'wave deformation', 'sinusoidal displacement'),
    definition='A shape is bent into a smooth wave whose crests keep sliding along it, '
               'so it ripples in place without travelling anywhere.',
    phrasings=('make the bar wave like a flag in the wind',
               'ripple this line with a rolling sine wave',
               'bend the shape into waves that keep moving along it'),
    related=('wave-deformer', 'sine-wave-text', 'wave-stagger', 'oscillation', 'wobble', 'ocean-waves'),
    api=('videobuilder.capabilities.shapes.sine_wave_distortion.sine_warp',
         'videobuilder.paths.resample', 'videobuilder.paths.draw'),
    demo=lambda: demo.film(draw),
)
