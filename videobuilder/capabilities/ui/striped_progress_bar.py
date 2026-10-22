"""Striped Progress Bar: a determinate progress bar whose fill is covered in
slanted stripes that keep sliding along it, so the bar looks busy even while
the amount filled holds still."""
import math

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Technique


def draw_striped_bar(cv, x, y, w, h, p, t, fill=demo.ACCENT, stripe=demo.INK, track=demo.LINE,
                     pitch=None, slant=1.0, speed=1.0, stripe_alpha=0.22, radius=None):
    """A progress bar with its top-left at (x, y), `w` by `h`, filled to
    `p` (0 -> 1) of its width. The fill carries diagonal stripes of `stripe`
    at `stripe_alpha`, one every `pitch` px (default `2 * h`), leaning by
    `slant` (horizontal shift per px of height); they move `speed` pitches
    per second at time `t` seconds, towards the filled end. `track` (or
    None) draws the empty bar behind. Returns the Box of the filled part."""
    r = h / 2 if radius is None else radius
    pitch = pitch or 2 * h
    if track:
        cv.rect(x, y, w, h, track, radius=r)
    fw = w * vb.clamp01(p)
    if fw <= 0:
        return vb.Box(x, y, 0, h)
    with cv.clip(x, y, fw, h, radius=min(r, fw / 2)):
        cv.rect(x, y, fw, h, fill)
        lean = slant * h
        shift = (t * speed % 1.0) * pitch
        c = cv.ctx
        k = math.floor((-lean - shift) / pitch) - 1
        while True:
            sx = x + k * pitch + shift
            if sx > x + fw:
                break
            c.move_to(sx + lean, y)
            c.line_to(sx + lean + pitch / 2, y)
            c.line_to(sx + pitch / 2, y + h)
            c.line_to(sx, y + h)
            c.close_path()
            k += 1
        c.set_source_rgba(*rgba(stripe, stripe_alpha))
        c.fill()
    return vb.Box(x, y, fw, h)


def draw(n, cv):
    t = n / demo.FPS
    w, h = 900, 56
    x, y = (demo.W - w) / 2, (demo.H - h) / 2
    p = 0.15 + 0.7 * vb.ease_in_out_quart(demo.phase(n, 0.3, 2.6))
    box = draw_striped_bar(cv, x, y, w, h, p, t, fill='#f2b705', stripe='#7a4a00', stripe_alpha=0.45,
                           track='#2a2f38')
    f = demo.font(34, 700)
    vb.text.draw(cv, ['Uploading'], f, x, y - 64, demo.INK)
    pct = f'{round(p * 100)}%'
    vb.text.draw(cv, [pct], f, x + w - vb.text.measure(pct, f), y - 64, demo.MUTED)
    cv.mark('bar', *box)


TECHNIQUE = Technique(
    id='striped-progress-bar',
    name='Striped progress bar',
    family='ui',
    group='Loaders',
    aliases=('animated stripes', 'barber pole', 'striped rotation', 'rotating stripes', 'stripe spin'),
    definition='A progress bar whose filled portion is painted with slanted stripes that keep '
               'scrolling sideways, showing work in progress even when the fill barely moves.',
    phrasings=('a loading bar with moving diagonal stripes on it',
               'the candy-striped progress bar that looks like it is crawling',
               'make the upload bar have those animated barber-pole stripes'),
    related=('refresh-bar', 'vhs-tracking-bar', 'copper-bars', 'scanline-jitter', 'percentage-fill-bar',
             'speed-lines'),
    api=('videobuilder.techniques.ui.striped_progress_bar.draw_striped_bar',),
    demo=lambda: demo.film(draw),
)
