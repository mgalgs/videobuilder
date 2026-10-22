"""Film edge frame: the picture sits inside a cell of dark film stock, with a
row of rounded sprocket holes above and below it and small printed edge
markings (gauge, frame number) in the margin, like a frame of 35mm film."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

STOCK = '#0b0c0e'      # the film base around the picture
HOLE = '#c9cbcf'       # light showing through the sprocket holes
EDGE_INK = '#e7a93a'   # the printed edge markings
HOLES = 4              # perforations per frame on each edge, as on 35mm


def film_edge_frame(cv, x, y, w, h, picture=None, number=24, label='35MM', holes=HOLES,
                    stock=STOCK, hole=HOLE, ink=EDGE_INK, margin=0.2):
    """Draw one frame of film filling the box (x, y, w, h): `stock`-coloured
    base, `holes` rounded sprocket holes along the top and bottom edges, edge
    print in `ink` (`label` and the frame `number` above the picture,
    `number` with an `A` below), and `picture(cv, box)` drawn clipped into
    the picture area. `margin` is the sprocket band's share of the height on
    each side. Returns the picture area's Box.

    Lay cells side by side (each `w` apart, `number` counting up) for a strip;
    shift their `x` to run the strip through."""
    band = h * margin
    cv.rect(x, y, w, h, stock)
    hw, hh = w / holes * 0.42, band * 0.42
    for i in range(holes):
        hx = x + (i + 0.5) * w / holes - hw / 2
        for hy in (y + band * 0.18, y + h - band * 0.18 - hh):
            cv.rect(hx, hy, hw, hh, hole, radius=min(hw, hh) * 0.3)
    pad = w * 0.035
    box = vb.Box(x + pad, y + band, w - 2 * pad, h - 2 * band)
    if picture is not None:
        with cv.clip(*box, radius=2):
            picture(cv, box)
    f = demo.mono(max(6.0, band * 0.17), 700)
    ty = y + band * 0.68
    vb.text.draw(cv, [f'{label}  ▸ {number}'], f, box.x, ty, ink)
    by = y + h - band * 0.88
    vb.text.draw(cv, [f'{number}A'], f, box.x + box.w - vb.text.measure(f'{number}A', f), by, ink)
    vb.text.draw(cv, ['◂ SAFETY FILM'], f, box.x, by, ink, alpha=0.7)
    return box


def _picture(cv, box):
    """A small sunset scene, so each frame reads as a photograph on the stock."""
    img = demo.photo()
    cv.image(img, *box.cover(img.w, img.h))


def draw(n, cv):
    cell_w, cell_h = 520, 440
    y = (demo.H - cell_h) / 2
    # The strip pulls in from the right and settles with frame 24 centred.
    p = vb.ease_out_quint(demo.phase(n, 0.1, 1.9))
    centre = (demo.W - cell_w) / 2
    x0 = centre - 2 * cell_w + (1 - p) * 4.5 * cell_w
    for i in range(7):
        x = x0 + i * cell_w
        if x + cell_w < 0 or x > demo.W:
            continue
        box = film_edge_frame(cv, x, y, cell_w, cell_h, picture=_picture, number=22 + i)
        if i == 2:
            cv.mark('frame', *box)
    # Once it lands, the title fades up inside the settled frame.
    t = demo.phase(n, 1.9, 2.4)
    if t > 0:
        demo.word(cv, 'MOTION', demo.W / 2, demo.H / 2 + 60, size=64, alpha=t)


TECHNIQUE = Technique(
    id='film-edge-frame',
    name='Film edge frame',
    family='vfx',
    group='Film & analog',
    aliases=('sprocket border', 'film strip frame', 'film edge markings', 'film perforation border'),
    definition='The shot is framed by a band of dark film stock, punched with rounded sprocket holes '
               'and printed with tiny frame numbers, so it looks like one cell of a strip of 35mm film.',
    phrasings=('put my image inside a film strip with the little holes along the edges',
               'make the shot look like a frame cut from a reel of movie film',
               'add a filmstrip border with frame numbers printed on it'),
    related=('linear-wipe', 'hard-cut', 'crt-scanlines', 'diagonal-wipe', 'fresnel-edge-glow',
             'crt-curvature'),
    api=('videobuilder.techniques.vfx.film_edge_frame.film_edge_frame',),
    demo=lambda: demo.film(draw),
)
