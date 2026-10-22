"""Chroma key: every pixel close to one backdrop colour turns transparent, so
the subject shot in front of it can sit over any other picture."""
from functools import lru_cache

from PIL import Image as PILImage, ImageChops

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

GREEN = (0, 177, 64)
BLUE = (0, 71, 187)


def chroma_key(img, key=GREEN, tolerance=60, softness=30, despill=1.0):
    """`img` (a `vb.Image` or a PIL image) with the backdrop colour `key`
    keyed out, as a `vb.Image` with an alpha matte, ready for `cv.image`.

    A pixel whose every channel is within `tolerance` (0-255) of `key` goes
    fully transparent; the matte then ramps to opaque over the next
    `softness` levels, so edges and uneven lighting stay soft. `despill`
    (0-1) pulls the key's strongest channel down toward the larger of the
    other two, taking the backdrop's colour cast off the subject's edges. Raise `tolerance`
    over time to watch the backdrop dissolve, darkest-lit parts last."""
    src = getattr(img, '_pil', img).convert('RGBA')
    r, g, b, a = src.split()
    chans = [r, g, b]
    dist = None
    for ch, k in zip(chans, key):
        d = ImageChops.difference(ch, PILImage.new('L', src.size, k))
        dist = d if dist is None else ImageChops.lighter(dist, d)
    soft = max(1e-6, softness)
    matte = dist.point([round(255 * vb.clamp01((v - tolerance) / soft)) for v in range(256)])
    if despill > 0:
        i = max(range(3), key=lambda c: key[c])
        others = [chans[c] for c in range(3) if c != i]
        capped = ImageChops.darker(chans[i], ImageChops.lighter(*others))
        chans[i] = PILImage.blend(chans[i], capped, min(1.0, despill))
    return vb.Image.from_pil(PILImage.merge('RGBA', (*chans, ImageChops.multiply(a, matte))))


# ---- demo ----
SW, SH = 1200, 675                      # the plate's own size, in its px
PW, PH = 720, 405                       # where it sits in the frame, in frame px
PX, PY = (demo.W - PW) / 2, (demo.H - PH) / 2 - 24


@lru_cache(maxsize=1)
def _plate():
    """A presenter in front of an unevenly lit green screen, as a PIL image."""
    cv = vb.Canvas(SW, SH)
    for i in range(40, 0, -1):            # brighter in the middle, falling off to the corners
        t = i / 40
        lit = 1 - t
        col = '#%02x%02x%02x' % (0, round(120 + 70 * lit), round(42 + 26 * lit))
        cv.sector(SW / 2, SH * 0.45, SW * 0.78 * t, 0, 6.2832, col)
    cx, base = SW / 2, SH
    cv.rect(cx - 190, base - 250, 380, 300, demo.ACCENT, radius=150)          # shoulders
    cv.rect(cx - 40, base - 300, 80, 70, '#d9a27a', radius=20)                # neck
    demo.dot(cv, cx, base - 380, r=110, color='#e6b48c')                      # head
    cv.sector(cx, base - 400, 116, 3.3, 6.12, '#2b1d17')                      # hair
    demo.card(cv, cx + 330, base - 330, w=220, h=140, color=demo.INK)        # a prop card
    data = cv.bgra()
    return PILImage.frombuffer('RGBA', (SW, SH), data, 'raw', 'BGRA', 0, 1).convert('RGB')


def _checker(cv, cell=24):
    cv.rect(PX, PY, PW, PH, '#3a3d45')
    for j in range(int(PH // cell) + 1):
        for i in range(j % 2, int(PW // cell) + 1, 2):
            cv.rect(PX + i * cell, PY + j * cell, min(cell, PW - i * cell), min(cell, PH - j * cell), '#2a2c33')


def draw(n, cv):
    key = demo.phase(n, 0.5, 1.6)
    swap = demo.phase(n, 1.8, 2.4)
    with cv.clip(PX, PY, PW, PH, radius=12):
        if key <= 0:
            cv.image(vb.Image.from_pil(_plate()), PX, PY, PW, PH)
        else:
            _checker(cv)
            if swap > 0:
                photo = demo.photo()
                cv.image(photo, *vb.Box(PX, PY, PW, PH).cover(photo.w, photo.h), alpha=swap)
            # from -softness (nothing keyed) up to the darkest corner of the screen
            tol = -25 + 95 * vb.ease_in_out_quart(key)
            cv.image(chroma_key(_plate(), tolerance=tol, softness=25, despill=key), PX, PY, PW, PH)
    cv.mark('plate', PX, PY, PW, PH)
    label = 'green screen' if key <= 0 else 'keying out green' if swap <= 0 else 'composited over a new background'
    demo.word(cv, label, demo.W / 2, PY + PH + 36, color=demo.MUTED, font=demo.mono(24, 600))
    cv.rect(PX + 16, PY + 16, 30, 30, '#%02x%02x%02x' % GREEN, radius=6)    # the key colour
    cv.outline(PX + 16, PY + 16, 30, 30, demo.INK, width=2, radius=6)


CAPABILITY = Capability(
    id='chroma-key',
    name='Chroma key',
    family='vfx',
    group='Keying & mattes',
    aliases=('green screen', 'blue screen', 'color key', 'colour key', 'keying'),
    definition='Everything in a shot that matches one solid backdrop colour is cut away, '
               'leaving the subject free to be placed on top of a different background.',
    phrasings=('remove the green screen behind the presenter and put them over this shot',
               'key out the blue background so only the person is left',
               'make the green backdrop see-through and drop a new scene in behind'),
    related=('scroll-linked-background-shift', 'night-vision', 'keystroke-overlay', 'screen-blend',
             'rgb-channel-split', 'chroma-bleed'),
    api=('videobuilder.capabilities.vfx.chroma_key.chroma_key',),
    demo=lambda: demo.film(draw),
)
