"""Data bending: a picture's raw pixel bytes are edited as if they were any
other file -- runs dropped, copied over, overwritten -- and read back as an
image, so whole stretches of it slip sideways, swap colour channels and
repeat in hard horizontal bands."""
import random
from functools import lru_cache

from PIL import Image as PILImage

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _edits(seed, w, h, count):
    """`count` byte edits on a `w` x `h` RGB buffer, the same list for the same
    seed, so a larger `count` only adds edits on top of the smaller one's."""
    rng = random.Random(seed)
    row = w * 3
    out = []
    for _ in range(count):
        kind = rng.choice(('slip', 'slip', 'repeat', 'stamp'))
        at = rng.randrange(h) * row + rng.randrange(row)
        if kind == 'slip':
            # Drop a few bytes here and pad them back a band later: everything in
            # between slides along and, unless the count is a multiple of 3,
            # reads its channels in the wrong order.
            out.append(('slip', at, rng.randrange(1, 3 * w // 4), rng.randint(2, h // 6) * row))
        elif kind == 'repeat':
            # One row's worth of bytes copied down over the rows below it.
            out.append(('repeat', at, row + rng.randrange(-6, 7), rng.randint(2, h // 10)))
        else:
            # A run overwritten with one repeated byte triple: a flat colour bar.
            out.append(('stamp', at, rng.randint(row // 3, row * 3),
                        bytes(rng.choice((0, 40, 120, 200, 255)) for _ in range(3))))
    return out


def bend_bytes(data, w, h, edits):
    """`data`, raw RGB bytes of a `w` x `h` image, with `edits` (from `_edits`)
    applied in order. The result is always the same length as `data`."""
    buf = bytearray(data)
    size = len(buf)
    for e in edits:
        kind, at = e[0], e[1]
        if kind == 'slip':
            n, span = e[2], e[3]
            end = min(size, at + span)
            seg = buf[at + n:end] + buf[at:at + n]
            buf[at:at + len(seg)] = seg
        elif kind == 'repeat':
            stride, times = e[2], e[3]
            chunk = buf[at:at + stride]
            for k in range(1, times + 1):
                s = at + k * stride
                if s >= size:
                    break
                buf[s:s + len(chunk)] = chunk[:size - s]
        else:
            n, triple = e[2], e[3]
            n = min(n, size - at)
            buf[at:at + n] = (triple * (n // 3 + 1))[:n]
    return bytes(buf[:size])


@lru_cache(maxsize=64)
def _bent(img, count, seed, width):
    pil = img._pil.convert('RGB')
    if width and pil.width > width:
        pil = pil.resize((width, round(pil.height * width / pil.width)), PILImage.BILINEAR)
    w, h = pil.size
    out = bend_bytes(pil.tobytes(), w, h, _edits(seed, w, h, count))
    return vb.Image.from_pil(PILImage.frombytes('RGB', (w, h), out))


def data_bend(img, amount, seed=0, edits=16, width=480):
    """`img` (a `vb.Image`) with its raw bytes corrupted: `amount` 0 -> 1 applies
    0 -> `edits` byte edits (slipped runs, repeated rows, overwritten bars),
    each new one added on top of the last, so a rising amount builds the damage
    up. The bytes are bent at `width` px wide (the look is in the bands, not
    the detail; draw the result scaled up). The same arguments give the same
    image, cached, so it is cheap to call per frame; change `seed` for a
    different corruption."""
    return _bent(img, round(vb.clamp01(amount) * edits), seed, width)


def draw(n, cv):
    img = demo.photo()
    amount = demo.phase(n, 0.3, 2.2)
    # The odd frame re-reads with a different corruption, the way a bent file
    # flickers when it is re-decoded.
    seed = 3 if amount < 0.3 or n % 9 else 11
    bent = data_bend(img, amount, seed=seed)
    cv.image(bent, *vb.Box.of(cv).cover(bent.w, bent.h))


CAPABILITY = Capability(
    id='data-bending',
    name='Data bending',
    family='vfx',
    group='Glitch',
    aliases=('hex glitch', 'byte corruption', 'file corruption glitch', 'databending'),
    definition='The picture looks like a damaged file read back anyway: stretches of it slide sideways '
               'with their colours swapped, and rows repeat or turn into flat bars of colour.',
    phrasings=('make the image look like a corrupted file',
               'break the photo apart into smeared, wrong-coloured stripes like broken data',
               'glitch the picture as if its bytes got scrambled'),
    related=('glitch-text', 'glitch-transition', 'glitch-sound', 'scanline-tear', 'pixel-sort-text',
             'blur-up-image-load'),
    api=('videobuilder.capabilities.vfx.data_bending.data_bend',
         'videobuilder.capabilities.vfx.data_bending.bend_bytes'),
    demo=lambda: demo.film(draw),
)
