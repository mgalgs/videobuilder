"""Tape wobble: the whole picture sways sideways in a slow, uneven wave that
runs down the frame, as if a worn tape were wavering in speed under the
playback head."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ...canvas import Canvas


def wobble_offset(y, t, amount=1.0, shift=10.0, wavelength=220.0, speed=0.6, seed=0):
    """The sideways offset in px of the picture row at height `y` (film px)
    at time `t` (seconds), at strength `amount` (0 -> 1). Two slow waves of
    different lengths roll down the frame at different speeds, so the bend
    never repeats exactly; a slower swell on top makes the whole sway surge
    and ease like a tape drifting off speed. `shift` is the largest offset,
    `wavelength` the main wave's height in px, `speed` how many waves pass a
    row each second."""
    if amount <= 0:
        return 0.0
    ph = seed * 1.618
    wave = (0.65 * math.sin(2 * math.pi * (y / wavelength - speed * t) + ph)
            + 0.35 * math.sin(2 * math.pi * (y / (wavelength * 0.37) - speed * 1.7 * t) + 2.1 + ph))
    swell = 0.75 + 0.25 * math.sin(2 * math.pi * 0.45 * t + 0.8 + ph)
    drift = 0.3 * math.sin(2 * math.pi * 0.23 * t + ph)   # the whole picture leans a little, then back
    return shift * amount * (wave * swell + drift)


def tape_wobble(cv, draw, t, amount=1.0, strip=2, **kw):
    """Draw `draw(cv)` with tape wobble at time `t` (seconds) and strength
    `amount` (0 -> 1): the scene is drawn once offscreen, then laid back
    down in horizontal strips `strip` device px tall, each slid sideways by
    `wobble_offset` for its row (`kw` goes there). Edges smear outward
    rather than showing a gap, the way a wavering picture does on a set. At
    `amount` 0 it is `draw(cv)` untouched.

    In a film, wrap any shot: `tape_wobble(cv, lambda c: scene(c, f), f.t, amount=0.6)`."""
    if amount <= 0:
        return draw(cv)
    sub = Canvas(cv.width, cv.height, scale=cv.scale, format=cv.format)
    sub.ctx.set_matrix(cv.ctx.get_matrix())
    draw(sub)
    sub.surface.flush()
    k = cv.scale
    dev_h = sub.surface.get_height()
    pattern = cairo.SurfacePattern(sub.surface)
    pattern.set_extend(cairo.EXTEND_PAD)
    c = cv.ctx
    c.save()
    c.identity_matrix()
    dev_w = sub.surface.get_width()
    strip = max(1, int(strip))
    for top in range(0, dev_h, strip):
        dx = wobble_offset((top + strip / 2) / k, t, amount, **kw) * k
        c.save()
        c.rectangle(0, top, dev_w, strip)
        c.clip()
        pattern.set_matrix(cairo.Matrix(x0=-dx))
        c.set_source(pattern)
        c.paint()
        c.restore()
    c.restore()


def _test_card(cv):
    """The demo's picture: the kit photo with a column of bars and a framed
    card, so straight vertical edges show the bend."""
    img = demo.photo()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))
    bars = ('#e9e6df', '#e6c84a', '#4ac7c9', '#5fbf5a', '#c64fb7', '#d9483b', '#3f55c9')
    bw, bh = 58, 270
    x0, y0 = demo.W / 2 - bw * len(bars) / 2, demo.H / 2 - bh / 2 - 15
    cv.shadow(x0, y0, bw * len(bars), bh, dy=6, blur=16, color=(0, 0, 0, 0.5))
    for i, col in enumerate(bars):
        cv.rect(x0 + i * bw, y0, bw, bh, col)
    cv.rect(x0, y0 + bh, bw * len(bars), 36, '#15161a')
    cv.mark('bars', x0, y0, bw * len(bars), bh + 36)


def draw(n, cv):
    t = n / demo.FPS
    amount = 0.45 + 0.55 * math.sin(math.pi * demo.phase(n, 0.2, 2.8)) ** 2   # surges mid-clip
    tape_wobble(cv, _test_card, t, amount, shift=14, seed=1)
    vb.text.draw(cv, ['PLAY'], demo.mono(24, 700), 36, 28, demo.INK)
    vb.text.draw(cv, [f'0:00:{int(t):02d}'], demo.mono(24, 700), demo.W - 160, 28, demo.INK)


CAPABILITY = Capability(
    id='tape-wobble',
    name='Tape wobble',
    family='vfx',
    group='VHS & tape',
    aliases=('head wobble', 'tape flutter', 'analog wow', 'wow and flutter', 'VHS wobble'),
    definition='The picture sways left and right in a slow wave that rolls down the screen, '
               'bending straight upright edges into soft curves like an old tape playing unevenly.',
    phrasings=('make it look like a worn VHS where the image wavers side to side',
               'give the footage that wobbly, warped old-tape sway',
               'bend the frame in slow sideways waves like the tape is stretching'),
    related=('rolling-shutter-wobble', 'scanline-jitter', 'handheld-shake', 'wobble', 'wiggle-path',
             'play-pause-morph'),
    api=('videobuilder.capabilities.vfx.tape_wobble.tape_wobble',
         'videobuilder.capabilities.vfx.tape_wobble.wobble_offset'),
    demo=lambda: demo.film(draw),
)
