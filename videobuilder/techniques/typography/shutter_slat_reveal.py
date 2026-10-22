"""Shutter Slat Reveal: a panel of horizontal slats covers the text, then the
slats turn on their long axis one after another, each narrowing to an edge,
so the words show through the widening gaps between them."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def slat_openings(p, slats, stagger=0.45, ease=vb.ease_in_out_quart):
    """How far each of `slats` slats has turned at progress `p` (0 -> 1), top
    first: 0 is closed (flat, covering), 1 is open (edge-on). Each slat turns
    over `1 - stagger` of the reveal, the starts spread across `stagger`."""
    span = 1 - stagger
    return [ease(vb.clamp01((p - stagger * i / max(1, slats - 1)) / span)) for i in range(slats)]


def draw_shutter(cv, content, x, y, w, h, p, slats=8, color=demo.ACCENT, shade='#000000', **kw):
    """Draw `content(cv)` behind a shutter of `slats` horizontal slats filling
    the box (x, y, w, h), opened to progress `p` (0 -> 1). Each slat turns
    about its centre line, so its visible height shrinks from the full band
    to nothing and the content appears in the gaps above and below it; a
    turning slat darkens toward `shade`. `kw` goes to `slat_openings`.

    `content` draws in film coordinates and is clipped to the box, so a film
    can pass any drawing, e.g. `lambda c: demo.word(c, 'OPEN', cx, cy)`."""
    with cv.clip(x, y, w, h):
        if p > 0:
            content(cv)
        band = h / slats
        for i, o in enumerate(slat_openings(p, slats, **kw)):
            sh = band * (1 - o)
            if sh <= 0.5:
                continue
            sy = y + i * band + (band - sh) / 2
            cv.rect(x, sy, w, sh, color)
            cv.rect(x, sy, w, sh, shade, alpha=0.55 * o)
            cv.rect(x, sy, w, min(2.0, sh), '#ffffff', alpha=0.25 * (1 - o))
    cv.mark('shutter', x, y, w, h)


def draw(n, cv):
    w, h = 760, 270
    x, y = (demo.W - w) / 2, (demo.H - h) / 2

    def content(c):
        c.rect(x, y, w, h, demo.INK)
        demo.word(c, 'NOW OPEN', demo.W / 2, demo.H / 2, size=116, color=demo.BG, weight=900)

    draw_shutter(cv, content, x, y, w, h, demo.phase(n, 0.4, 2.5), slats=7)


TECHNIQUE = Technique(
    id='shutter-slat-reveal',
    name='Shutter slat reveal',
    family='typography',
    group='Masking and clipping',
    aliases=('shutter reveal', 'louvre reveal', 'slat reveal', 'blinds text reveal'),
    definition='A stack of horizontal slats covering the text turns edge-on one after another, '
               'top to bottom, so the words appear through the opening gaps.',
    phrasings=('the title is hidden behind slats that flip open like window shutters',
               'reveal the words by rotating a set of blinds open over them',
               'strips covering the text turn sideways one by one to show it'),
    related=('venetian-blinds-wipe', 'text-mask-reveal', 'curtain-reveal', 'shutter-wipe',
             'image-hover-mask-reveal', 'uncover'),
    api=('videobuilder.techniques.typography.shutter_slat_reveal.draw_shutter',
         'videobuilder.techniques.typography.shutter_slat_reveal.slat_openings'),
    demo=lambda: demo.film(draw),
)
