"""Stamp impression: a word drops onto the surface from oversize, faint and
grey, lands with a slight squash and a flash of light at the moment of
contact, then sits pressed in at its final size."""
import videobuilder as vb
from videobuilder.type.kit import blurred

from .. import _demo as demo
from ..schema import Technique


def _mix(a, b, t):
    a, b = a.lstrip('#'), b.lstrip('#')
    return '#' + ''.join(f'{round(int(a[i:i + 2], 16) * (1 - t) + int(b[i:i + 2], 16) * t):02x}' for i in (0, 2, 4))


def stamp(p, start_scale=2.2, press=0.3, squash=0.06):
    """The stamp at progress `p` (0 -> 1) as `(scale, ink, flash)`. Until
    `press` the word falls from `start_scale` to 1 on an accelerating curve
    and `ink` (how solid it is, 0.25 -> 1) rises with it; at contact it dips
    `squash` below its size and springs back. `flash` jumps to 1 at contact
    and fades by the end."""
    p = vb.clamp01(p)
    if p < press:
        q = p / press
        return 1 + (start_scale - 1) * (1 - q) ** 3, 0.25 + 0.75 * q ** 2, 0.0
    k = (p - press) / (1 - press)
    dip = squash * (1 - k / 0.25) if k < 0.25 else 0.0
    return 1 - dip, 1.0, (1 - k) ** 3


def draw_stamp(cv, text, font, cx, cy, p, color, faint=None, glow=None, **kw):
    """Draw `text` stamping on at progress `p`, centred at (cx, cy). It
    starts tinted toward `faint` (default: `color` at a quarter strength) and
    turns solid `color` as it lands; the contact flash is a blur of `glow`
    (default `color`). `kw` goes to `stamp`. Returns the Box of the word at
    rest."""
    scale, ink, flash = stamp(p, **kw)
    w, h = vb.text.block_size([text], font)
    x, y = cx - w / 2, cy - h / 2
    box = vb.Box(x, y, w, h)

    def word(c, col=color, alpha=1.0):
        vb.text.draw(c, [text], font, x, y, col, alpha=alpha)

    with cv.layer(dx=cx * (1 - scale), dy=cy * (1 - scale), scale=scale):
        if flash > 0.01:
            r = h * (0.18 + 0.25 * (1 - flash))
            blurred(cv, box, r, lambda c: word(c, glow or color), alpha=min(1.0, 1.3 * flash))
        if faint:
            word(cv, _mix(faint, color, ink))
        else:
            word(cv, color, alpha=ink)
    return box


def draw(n, cv):
    f = demo.font(150, 900)
    box = draw_stamp(cv, 'MOTION', f, demo.W / 2, demo.H / 2, demo.phase(n, 0.3, 2.6), demo.INK,
                     faint=demo.MUTED, glow='#ffffff')
    cv.mark('text', *box)


TECHNIQUE = Technique(
    id='stamp-impression',
    name='Stamp impression',
    family='typography',
    group='Surface and light',
    aliases=('letterpress stamp', 'impact press text', 'stamp in'),
    definition='A word falls from oversize onto the frame, squashes slightly as it hits, '
               'and flares with light at the moment of contact before settling solid.',
    phrasings=('press the title onto the screen like a rubber stamp',
               'the word slams down from big to normal size with a flash when it lands',
               'make the headline look like it was pressed into the page'),
    related=('badge-stamp-impact', 'wipe-reveal', 'impact-shake', 'pixel-sort-text', 'per-character-fade-in',
             'hover-letter-displacement'),
    api=('videobuilder.techniques.typography.stamp_impression.draw_stamp',
         'videobuilder.techniques.typography.stamp_impression.stamp'),
    demo=lambda: demo.film(draw),
)
