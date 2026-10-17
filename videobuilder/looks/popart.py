"""Pop-art halftone: flat loud colours, Ben-Day dot fills and heavy black
outlines. The sky's and water's dots drift, a ray burst turns from the beacon
(or the sun), white wave lines roll, and a starburst springs in every two
beats -- with a word in it when the video passes one.

Options: `sfx` -- a short word for the burst ("POW!"), drawn with `font`
(a vb.Font, required with `sfx`); `burst` -- (x, y) for the burst's centre;
`burst_every` -- beats between bursts (2)."""
import dataclasses
import math

import cairo

from . import kit
from .look import Look
from .. import paths, text
from ..canvas import halftone_pattern
from ..ease import damped, spring

INK = '#111111'
# role -> (fill, halftone dot colour or None) its regions take in turn
FILLS = {
    'land': (('#ff4f8a', '#d81f6a'), ('#7ad84a', '#3a9a2a')),
    'building': (('#ffffff', None), ('#e8202a', None), ('#fff04a', None)),
    'figure': (('#e8202a', None), ('#ffffff', None)),
    'light': (('#fff04a', None),),
    'sky': (('#33c6e8', '#1f8fc8'),),
    'water': (('#2a4ad8', '#1a2a9a'),),
}


def _dots(cv, pitch, radius, colour, angle=0.0, dx=0.0, dy=0.0):
    pat = halftone_pattern(pitch, radius, angle=angle, color=colour)
    m = pat.get_matrix()
    m = cairo.Matrix(x0=-dx, y0=-dy).multiply(m) if (dx or dy) else m
    pat.set_matrix(m)
    cv.ctx.set_source(pat)
    cv.ctx.paint()


def paint(cv, scene, t, age, sfx=None, font=None, burst=None, burst_every=2):
    c = cv.ctx
    u = scene.u
    w, h = scene.w, scene.h
    sky_h = scene.sky_bottom
    cv.rect(0, 0, w, h, '#33c6e8')
    c.save()
    c.rectangle(0, 0, w, sky_h)
    c.clip()
    _dots(cv, 30 * u, 8 * u, '#1f8fc8', dx=40 * u * t, dy=25 * u * t)     # the dots drift
    ox, oy = scene.beacon or scene.sun_or_default()[:2]
    for i in range(16):                         # the burst of rays, turning
        a = 2 * math.pi * i / 16 + t * 0.9
        reach = 1.5 * max(w, h)
        kit.fill(cv, [(ox, oy), (ox + reach * math.cos(a - 0.06), oy + reach * math.sin(a - 0.06)),
                      (ox + reach * math.cos(a + 0.06), oy + reach * math.sin(a + 0.06))], '#fff04a', 0.75)
    c.restore()
    if scene.sun:
        mx, my, mr = scene.sun
        kit.fill(cv, kit.circle_pts(mx, my, mr), '#fff04a', outline=INK, width=9 * u)
        with kit.clip_to(cv, kit.circle_pts(mx, my, mr - 5 * u)):
            _dots(cv, 18 * u, 5 * u, '#f2a020', angle=0.5)
    if scene.horizon is not None:
        top = scene.horizon
        cv.rect(0, top, w, h - top, '#2a4ad8')
        c.save()
        c.rectangle(0, top, w, h - top)
        c.clip()
        _dots(cv, 24 * u, 7 * u, '#1a2a9a', dx=-30 * u * t)
        c.restore()
        row, y = 0, top + 60 * u
        while y < h:
            pts = []
            x = -20 * u
            while x < w + 40 * u:
                pts.append((x, y + 18 * u * math.sin(x / (50 * u) + t * 4 + row)))
                x += 20 * u
            paths.draw(cv, pts, '#ffffff', width=8 * u)
            y += 100 * u
            row += 1
    turn = kit.Turns(FILLS, {'building': (INK, None)}, thin=30 * u)
    for region in scene.regions:
        colour, dots = turn(region)
        x0, y0, rw, rh = region.bbox
        heavy = (9 if min(rw, rh) > 40 * u else 6) * u
        kit.fill(cv, region.points, colour)
        if dots:
            with kit.clip_to(cv, region.points):
                _dots(cv, 22 * u, 6 * u, dots, angle=0.8)
        elif region.role == 'building' and rh > 140 * u:
            kit.bands(cv, region.points, ('#e8202a', colour), 74 * u, offset=y0)
        kit.outline(cv, region.points, INK, heavy)
    # the starburst, springing in every `burst_every` beats
    since = kit.since_beat(t, scene.bpm, burst_every)
    s = spring(since, **damped(0.35, hz=3.0))
    if burst:
        bx, by = burst
    else:
        water = scene.open_water()
        bx = (water[0] + water[1]) / 2 if water else w * 0.6
        bx = min(max(bx, 220 * u), w - 220 * u)        # clear of the frame's edges, even at full spring
        by = sky_h * 0.85 if scene.horizon is not None else h * 0.75
    if s > 0.05:
        rx, ry = 190 * u * s, 130 * u * s
        star = [(bx + (rx if i % 2 == 0 else rx * 0.68) * math.cos(2 * math.pi * i / 24),
                 by + (ry if i % 2 == 0 else ry * 0.68) * math.sin(2 * math.pi * i / 24)) for i in range(24)]
        kit.fill(cv, star, '#fff04a', outline=INK, width=7 * u)
        if sfx and font:
            f = dataclasses.replace(font, size=max(1.0, font.size * max(0.2, min(s, 1.2))))
            tw = text.measure(sfx, f)
            if tw > rx * 1.3:                             # the word always fits inside the burst
                f = dataclasses.replace(f, size=max(1.0, f.size * rx * 1.3 / tw))
            lines = [sfx]
            tw, th = text.block_size(lines, f)
            text.draw(cv, lines, f, bx - tw / 2, by - th / 2, '#e8202a', align='center', width=tw)

LOOK = Look('pop-art', 'Pop-art halftone', 'dots drift, rays turn, a burst pops', paint,
            aliases=('pop', 'popart', 'comic', 'comic book', 'halftone', 'ben-day'))
