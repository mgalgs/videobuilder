"""Day-night cycle: one time-of-day value drives the sky gradient, the
colour and strength of the light falling on the scene, the sun going down,
the moon and stars coming out, so a still landscape passes from noon
through dusk into night."""
import math
import random
from dataclasses import dataclass

import cairo

import videobuilder as vb
from videobuilder import parallax, paths

from .. import _demo as demo
from ..schema import Capability


@dataclass(frozen=True)
class Light:
    """The look of one moment of the day. `top` and `horizon`: the sky's
    gradient. `tint`: the colour the light multiplies the scene by, and
    `strength` how much (0 = untouched, 1 = fully tinted). `stars`: how
    visible the stars are, 0 -> 1. Colours are 0-255 RGB tuples or hex."""
    top: object
    horizon: object
    tint: object
    strength: float
    stars: float


def _rgb(c):
    return tuple(255 * v for v in vb.rgba(c)[:3])


def _mix(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(_rgb(a), _rgb(b)))


DAY_TO_NIGHT = (
    (0.00, Light('#3f7fd8', '#a9d4f5', '#fff6e8', 0.00, 0.0)),   # midday
    (0.40, Light('#4a6fc0', '#f6c27a', '#ffd9a0', 0.25, 0.0)),   # golden hour
    (0.62, Light('#3a2f6b', '#f0705a', '#e08070', 0.55, 0.1)),   # dusk
    (0.80, Light('#151a3a', '#4a3a6a', '#5a68b0', 0.70, 0.6)),   # blue hour
    (1.00, Light('#05070f', '#141a33', '#33407a', 0.80, 1.0)),   # night
)


def light_at(t, keys=DAY_TO_NIGHT):
    """The `Light` at time of day `t` (0 -> 1 along `keys`, a sorted tuple of
    `(t, Light)`), blended smoothly between the two keys around it. Run `t`
    backwards for night into day."""
    t = vb.clamp01(t)
    for (t0, a), (t1, b) in zip(keys, keys[1:]):
        if t <= t1:
            k = (t - t0) / (t1 - t0) if t1 > t0 else 1.0
            k = k * k * (3 - 2 * k)  # smoothstep: no kink at the keys
            return Light(_mix(a.top, b.top, k), _mix(a.horizon, b.horizon, k), _mix(a.tint, b.tint, k),
                         a.strength + (b.strength - a.strength) * k, a.stars + (b.stars - a.stars) * k)
    return keys[-1][1]


def draw_sky(cv, light, x, y, w, h, star_seed=7, star_count=70):
    """Paint the sky for `light` into the box: a vertical gradient from
    `light.top` to `light.horizon`, with seeded stars faded in by
    `light.stars`."""
    c = cv.ctx
    g = cairo.LinearGradient(0, y, 0, y + h)
    g.add_color_stop_rgb(0, *vb.rgba(light.top)[:3])
    g.add_color_stop_rgb(1, *vb.rgba(light.horizon)[:3])
    c.save()
    c.rectangle(x, y, w, h)
    c.set_source(g)
    c.fill()
    c.restore()
    if light.stars > 0.01:
        rnd = random.Random(star_seed)
        for _ in range(star_count):
            sx, sy = x + rnd.random() * w, y + rnd.random() ** 1.6 * h * 0.8
            twinkle = 0.6 + 0.4 * rnd.random()
            demo.dot(cv, sx, sy, r=0.8 + 1.4 * rnd.random(), color='#ffffff', alpha=light.stars * twinkle)


def wash(cv, light, x, y, w, h):
    """Light what is already drawn in the box with `light`: multiply it by
    `light.tint` at `light.strength`, so the scene warms at dusk and goes
    cool and dark at night. Draw the landscape, then call this, then draw
    anything that glows by itself (lit windows, the moon) on top."""
    c = cv.ctx
    c.save()
    c.rectangle(x, y, w, h)
    c.clip()
    c.set_operator(cairo.OPERATOR_MULTIPLY)
    c.set_source_rgba(*vb.rgba(light.tint, light.strength))
    c.paint()
    c.restore()


def glow(cv, cx, cy, r, color, alpha=1.0):
    """A soft disc of light: a radial halo around a solid body of radius `r`."""
    c = cv.ctx
    rr, gg, bb = vb.rgba(color)[:3]
    g = cairo.RadialGradient(cx, cy, r * 0.8, cx, cy, r * 3.2)
    g.add_color_stop_rgba(0, rr, gg, bb, 0.35 * alpha)
    g.add_color_stop_rgba(1, rr, gg, bb, 0)
    c.save()
    c.arc(cx, cy, r * 3.2, 0, 2 * math.pi)
    c.set_source(g)
    c.fill()
    c.restore()
    demo.dot(cv, cx, cy, r=r, color=color, alpha=alpha)


def sky_path(t, x0, x1, top, bottom):
    """A point on the arc a sun travels as `t` goes 0 -> 1: from high on the
    left of `x0..x1` at `top` down past `bottom` on the right."""
    a = math.pi * (0.35 + 0.75 * t)
    return x0 + (x1 - x0) * (0.5 - 0.5 * math.cos(a)), bottom - (bottom - top) * math.sin(a)


# --- demo -------------------------------------------------------------------

W, H = demo.W, demo.H
FAR = parallax.ridge(W, 70, seed=4)
NEAR = parallax.ridge(W, 60, seed=9, bumps=(1, 2))


def _hills(cv, pts, y, color):
    paths.draw(cv, [(px, y + py) for px, py in pts] + [(W, H), (0, H)], color, fill=True)


def _house(cv, cx, base):
    cv.rect(cx - 50, base - 70, 100, 70, '#d9d2c3')
    paths.draw(cv, [(cx - 62, base - 68), (cx, base - 118), (cx + 62, base - 68)], '#b2483c', fill=True)
    cv.rect(cx - 12, base - 38, 24, 38, '#6b4a33')


def draw(n, cv):
    t = demo.phase(n, 0.25, 2.75)
    light = light_at(t)
    horizon = 330
    draw_sky(cv, light, 0, 0, W, horizon + 40)
    sx, sy = sky_path(t, 120, W - 120, 70, horizon + 60)
    glow(cv, sx, sy, 36, _mix('#fff1b0', '#ff7a3a', vb.clamp01(t / 0.62)))
    _hills(cv, FAR, horizon - 30, '#7fa7a0')
    _hills(cv, NEAR, horizon + 40, '#4f8a57')
    _house(cv, W * 0.32, horizon + 120)
    wash(cv, light, 0, 0, W, H)
    lit = vb.clamp01((t - 0.6) / 0.15)  # windows come on at dusk
    cv.rect(W * 0.32 + 20, horizon + 120 - 52, 20, 20, '#ffd27a', alpha=lit)
    cv.rect(W * 0.32 - 40, horizon + 120 - 52, 20, 20, '#ffd27a', alpha=lit)
    moon = vb.clamp01((t - 0.65) / 0.35)
    mx, my = W * 0.24, horizon - 40 - 200 * vb.ease_out_quint(moon)
    glow(cv, mx, my, 26, '#eef2ff', alpha=moon)
    cv.mark('sky', 0, 0, W, horizon)


CAPABILITY = Capability(
    id='day-night-cycle',
    name='Day-night cycle',
    family='camera',
    group='Lighting & surface',
    aliases=('time-of-day transition', 'sun cycle', 'time-of-day lighting', 'dusk transition'),
    definition='A scene stays put while its sky, light colour and brightness slide from bright daylight '
               'through a warm sunset into a dark, starry night.',
    phrasings=('have the landscape go from daytime to night',
               'let the sun set and the stars come out over the scene',
               'show the passing of a day with the light changing'),
    related=('synthwave-sun', 'color-cycling', 'palette-shift-transition', 'hue-cycle-fill',
             'night-vision', 'solarization'),
    api=('videobuilder.capabilities.camera.day_night_cycle.light_at',
         'videobuilder.capabilities.camera.day_night_cycle.draw_sky',
         'videobuilder.capabilities.camera.day_night_cycle.wash',
         'videobuilder.capabilities.camera.day_night_cycle.glow',
         'videobuilder.capabilities.camera.day_night_cycle.sky_path',
         'videobuilder.capabilities.camera.day_night_cycle.Light'),
    demo=lambda: demo.film(draw),
)
