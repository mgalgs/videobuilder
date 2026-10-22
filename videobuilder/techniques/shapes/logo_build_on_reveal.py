"""Logo build-on reveal: a logo's parts arrive one at a time in a set order
-- the mark's pieces, then each letter of the wordmark -- every part rising
into place from behind its own baseline, until the whole lockup stands."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def build_on(cv, parts, p, overlap=0.35, rise=1.0, pad=16, ease=vb.ease_out_back):
    """Draw `parts` building on in order at progress `p` (0 -> 1). Each part
    is `(box, draw)`: `box` the (x, y, w, h) it occupies at rest, `draw(cv)`
    drawing it there. Parts take turns, each starting once the one before is
    `overlap` of the way in; each slides up `rise` of its height from behind
    the bottom edge of its box (clipped there, `pad` of slack on the other
    sides) along `ease`. Parts not yet started draw nothing; at 1 all stand."""
    n = len(parts)
    if not n:
        return
    span = 1 / (1 + (n - 1) * (1 - overlap))
    for i, ((x, y, w, h), draw) in enumerate(parts):
        q = vb.clamp01((p - i * span * (1 - overlap)) / span)
        if q <= 0:
            continue
        if q >= 1:
            draw(cv)
            continue
        with cv.clip(x - pad, y - pad, w + 2 * pad, h + pad), cv.layer(dy=(1 - ease(q)) * rise * h):
            draw(cv)


def letters(text, font, x, y, color, alpha=1.0):
    """`text` from its top-left (x, y) as one build-on part per letter
    (spaces skipped), each drawing its glyph where the whole line puts it."""
    _, h = vb.text.block_size([text], font)
    out, left = [], x
    for ch in text:
        adv = vb.text.measure(ch, font)
        if not ch.isspace():
            out.append(((left, y, adv, h),
                         lambda cv, ch=ch, gx=left: vb.text.draw(cv, [ch], font, gx, y, color, alpha=alpha)))
        left += adv
    return out


def _logo(cx, cy):
    """The demo lockup centred on (cx, cy): a three-piece mark, then a wordmark."""
    f = demo.font(76, 800)
    text = 'NORTHWIND'
    tw, th = vb.text.block_size([text], f)
    m, gap = 96, 30
    x = cx - (m + gap + tw) / 2
    my = cy - m / 2
    k, r = m * 0.22, m * 0.15
    mark = [
        ((x, my, m, m), lambda cv: cv.rect(x, my, m, m, demo.ACCENT, radius=m * 0.2)),
        ((x + k, my + k, m - 2 * k, m - 2 * k),
         lambda cv: cv.rect(x + k, my + k, m - 2 * k, m - 2 * k, demo.BG, radius=m * 0.1)),
        ((x + m / 2 - r, my + m / 2 - r, 2 * r, 2 * r),
         lambda cv: demo.dot(cv, x + m / 2, my + m / 2, r=r, color=demo.TEAL)),
    ]
    return mark + letters(text, f, x + m + gap, cy - th / 2, demo.INK)


def draw(n, cv):
    parts = _logo(demo.W / 2, demo.H / 2)
    build_on(cv, parts, demo.phase(n, 0.3, 2.4))
    (x, y, _, h), (lx, _, lw, _) = parts[0][0], parts[-1][0]
    cv.mark('logo', x, y, lx + lw - x, h)


TECHNIQUE = Technique(
    id='logo-build-on-reveal',
    name='Logo build-on reveal',
    family='shapes',
    group='Logo animation',
    aliases=('letter-by-letter build', 'typewriter logo', 'sequential letter reveal', 'logo build'),
    definition='A logo assembles itself one piece at a time in a set order, the mark first and then each letter, '
               'every new part rising into place beside the ones already there.',
    phrasings=('have the logo put itself together bit by bit',
               'bring the logo in one letter after another until it is complete',
               'the brand mark pops in first, then the name builds up after it'),
    related=('line-draw-logo-reveal', 'handwriting-reveal', 'light-trail-logo-reveal', 'wireframe-reveal',
             'typewriter-reveal', 'text-mask-reveal'),
    api=('videobuilder.techniques.shapes.logo_build_on_reveal.build_on',
         'videobuilder.techniques.shapes.logo_build_on_reveal.letters'),
    demo=lambda: demo.film(draw),
)
