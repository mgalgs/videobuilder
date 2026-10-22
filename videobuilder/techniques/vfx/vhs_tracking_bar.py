"""VHS Tracking Bar: a ragged band of snowy static and torn, sideways-shifted
picture crawls up the frame, the way a mistracked tape plays back."""
import math
import random

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def tracking_y(p, height, bar=120, top=None, bottom=None):
    """Where the bar's centre sits at progress `p` (0 -> 1): starting just below
    `bottom` (default the frame's foot) and crawling up past `top` (default 0),
    so `p` 0 and 1 both leave the picture clean."""
    top = -bar / 2 if top is None else top
    bottom = height + bar / 2 if bottom is None else bottom
    return bottom + (top - bottom) * vb.clamp01(p)


def vhs_tracking_bar(cv, y, bar=120, seed=0, shear=28, streaks=0.8, snow='#f2f2ee', strip=3):
    """Damage the picture already drawn on `cv` with a tracking band centred
    at `y` (frame px), `bar` tall. Inside it each thin `strip` of rows is
    shifted sideways by up to `shear` px, the band's top and bottom edges are
    ragged, and `streaks` (0 -> 1) sets how thick the bright horizontal noise
    dashes are. Change `seed` every frame for live noise (e.g. `seed=n`).

    Draw the scene first, then call this; animate `y` with `tracking_y`."""
    rng = random.Random(f'vhs:{seed}')
    s = cv.scale
    cv.surface.flush()
    snap = cairo.ImageSurface(cairo.FORMAT_ARGB32, cv.surface.get_width(), cv.surface.get_height())
    sc = cairo.Context(snap)
    sc.set_source_surface(cv.surface, 0, 0)
    sc.paint()

    c = cv.ctx
    c.save()
    c.identity_matrix()  # work in device px; the snapshot is device px too
    top, height = (y - bar / 2) * s, bar * s
    rows = max(1, round(strip * s))
    wobble = rng.uniform(0, math.tau)
    r = 0
    while r < height:
        # The edges are ragged: rows near them are only sometimes inside the band.
        edge = min(r, height - r) / height * 2  # 0 at the edges, 1 at the middle
        if edge > 0.25 or rng.random() < edge * 4:
            ry = top + r
            core = math.sin(math.pi * r / height)
            dx = (rng.uniform(-1, 1) * 0.6 + math.sin(wobble + r * 0.07) * 0.4) * shear * s * core
            c.save()
            c.rectangle(0, ry, snap.get_width(), rows)
            c.clip()
            c.set_source_surface(snap, dx, 0)
            c.paint()
            c.set_source_rgba(0, 0, 0, 0.25 * core)
            c.paint()
            c.restore()
            # Bright dashes of tape noise, thicker towards the middle of the band.
            sr, sg, sb, _ = vb.rgba(snow)
            for _ in range(int(1 + 5 * streaks * core)):
                if rng.random() > 0.35 + 0.6 * streaks * core:
                    continue
                x0 = rng.uniform(-0.1, 1.0) * snap.get_width()
                length = rng.uniform(0.02, 0.35) * snap.get_width()
                c.set_source_rgba(sr, sg, sb, rng.uniform(0.35, 0.95))
                c.rectangle(x0, ry + rng.uniform(0, rows * 0.6), length, max(1.0, rows * rng.uniform(0.3, 0.7)))
                c.fill()
        r += rows
    c.restore()


def draw(n, cv):
    img = demo.photo()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))
    f = demo.mono(40, 700)
    vb.text.draw(cv, ['PLAY ▶'], f, 64, 48, demo.INK)
    y = tracking_y(demo.phase(n, 0.2, 2.8), demo.H, bar=150)
    vhs_tracking_bar(cv, y, bar=150, seed=n)
    cv.mark('bar', 0, y - 75, demo.W, 150)


TECHNIQUE = Technique(
    id='vhs-tracking-bar',
    name='VHS tracking bar',
    family='vfx',
    group='VHS & tape',
    aliases=('tape tracking lines', 'tracking noise', 'VHS tracking error'),
    definition='A wide strip of white static with frayed edges creeps up the picture, '
               'tearing the image inside it sideways like an old videotape that has slipped out of alignment.',
    phrasings=('make it look like a bad VHS tape with the noisy band rolling up the screen',
               'add that old video tracking glitch crawling through the shot',
               'a band of tape static drifting up over the footage'),
    related=('scanline-jitter', 'refresh-bar', 'striped-progress-bar', 'copper-bars', 'audio-waveform-bars',
             'glitch-transition'),
    api=('videobuilder.techniques.vfx.vhs_tracking_bar.vhs_tracking_bar',
         'videobuilder.techniques.vfx.vhs_tracking_bar.tracking_y'),
    demo=lambda: demo.film(draw),
)
