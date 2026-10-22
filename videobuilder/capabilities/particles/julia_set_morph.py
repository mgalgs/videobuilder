"""Julia Set Morph: a Julia fractal drawn with escape-time colouring while its
constant `c` travels a path, so the shape melts continuously from one form
(fat bubbles, say) to another (curled spirals, dust).

The fractal is computed per frame at the canvas's device resolution (capped
by `detail`), with numpy when it is installed and plain Python otherwise."""
import cmath
import math

from PIL import Image as PILImage

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

try:
    import numpy as np
except ImportError:  # optional: the plain-Python path below gives the same picture, slower
    np = None

# Escape-time palette stops, (t, rgb): the set itself is near-black, the
# escaping field fades from the background through violet and lavender to a
# hot rim right at the boundary.
PALETTE = ((0.0, (20, 21, 26)), (0.2, (24, 24, 40)), (0.45, (60, 54, 140)), (0.7, (140, 140, 240)), (0.9, (230, 230, 255)),
           (1.0, (255, 214, 120)))
INSIDE = (12, 12, 16)


def julia_constant(p, radius=0.7885, start=2.1, end=3.1):
    """A constant for progress `p` (0 -> 1) on the circle |c| = `radius`,
    from angle `start` to `end` radians. Near 0.7885 the circle stays close to
    the Mandelbrot boundary, where Julia sets are most varied, so sweeping it
    gives the classic morph."""
    return cmath.rect(radius, start + (end - start) * vb.clamp01(p))


def _ramp(t, palette):
    t = min(max(t, 0.0), 1.0)
    for (t0, c0), (t1, c1) in zip(palette, palette[1:]):
        if t <= t1:
            k = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            return tuple(round(a + (b - a) * k) for a, b in zip(c0, c1))
    return palette[-1][1]


def _lut(palette, inside, size=256):
    return [_ramp(i / (size - 1), palette) for i in range(size)] + [inside]


def _escape_numpy(c, w, h, cx, cy, span, iterations):
    xs = np.linspace(cx - span / 2, cx + span / 2, w)
    ys = np.linspace(cy + span * h / w / 2, cy - span * h / w / 2, h)
    z = xs[None, :] + 1j * ys[:, None]
    n = np.full(z.shape, -1.0)
    alive = np.ones(z.shape, bool)
    for i in range(iterations):
        z[alive] = z[alive] * z[alive] + c
        out = alive & (np.abs(z) > 4.0)
        az = np.abs(z[out])
        n[out] = np.maximum(i + 1 - np.log2(np.log2(az)), 0.0)  # smooth escape count
        alive &= ~out
        if not alive.any():
            break
    return n


def _escape_python(c, w, h, cx, cy, span, iterations):
    out = []
    x0, y0, tall = cx - span / 2, cy + span * h / w / 2, span * h / w
    for j in range(h):
        y = y0 - tall * j / (h - 1)
        for i in range(w):
            z = complex(x0 + span * i / (w - 1), y)
            n = -1.0
            for k in range(iterations):
                z = z * z + c
                if z.real * z.real + z.imag * z.imag > 16.0:
                    n = max(k + 1 - math.log2(math.log2(abs(z))), 0.0)
                    break
            out.append(n)
    return out


def julia_image(c, w, h, center=(0.0, 0.0), span=3.4, iterations=80, palette=PALETTE, inside=INSIDE):
    """A `w` x `h` `vb.Image` of the Julia set of `c`, centred on the complex
    point `center`, `span` wide on the real axis. Points that never escape in
    `iterations` steps are `inside`; the rest are coloured along `palette`
    ((t, rgb) stops) by a smoothed escape count, brightest at the boundary."""
    w, h = max(int(w), 2), max(int(h), 2)
    lut = _lut(palette, inside)
    top = len(lut) - 2
    if np is not None:
        n = _escape_numpy(c, w, h, center[0], center[1], span, iterations)
        t = np.sqrt(np.clip(n, 0, None) / iterations)
        idx = np.where(n < 0, top + 1, np.clip((t * top).astype(int), 0, top))
        rgb = np.asarray(lut, dtype=np.uint8)[idx]
        pil = PILImage.fromarray(rgb, 'RGB')
    else:
        n = _escape_python(c, w, h, center[0], center[1], span, iterations)
        data = bytearray()
        for v in n:
            data += bytes(lut[top + 1] if v < 0 else lut[min(int(math.sqrt(max(v, 0) / iterations) * top), top)])
        pil = PILImage.frombytes('RGB', (w, h), bytes(data))
    return vb.Image.from_pil(pil)


def draw_julia(cv, c, x, y, w, h, detail=480, **kw):
    """Draw the Julia set of `c` filling the box (x, y, w, h). It is computed
    at the canvas's device resolution, at most `detail` pixels wide, and
    scaled up to the box. Call it every frame with a moving `c` (see
    `julia_constant`) to morph it; `kw` goes to `julia_image`."""
    px = min(detail, max(8, round(w * cv.scale_factor())))
    img = julia_image(c, px, round(px * h / w), **kw)
    cv.image(img, x, y, w, h)


def draw(n, cv):
    p = demo.phase(n, 0.0, demo.SECONDS)
    c = julia_constant(p)
    draw_julia(cv, c, 0, 0, demo.W, demo.H, span=3.4)
    sign = '+' if c.imag >= 0 else '-'
    cv.rect(demo.W / 2 - 150, demo.H - 62, 300, 44, demo.BG, radius=22, alpha=0.8)
    demo.word(cv, f'c = {c.real:+.3f} {sign} {abs(c.imag):.3f}i', demo.W / 2, demo.H - 40,
              size=24, color=demo.INK, font=demo.mono(24, 600))
    cv.mark('fractal', 0, 0, demo.W, demo.H)


CAPABILITY = Capability(
    id='julia-set-morph',
    name='Julia set morph',
    family='particles',
    group='Fractals',
    aliases=('Julia morph', 'animated Julia'),
    definition='A Julia fractal whose constant drifts over time, so its lacy outline continuously '
               'reshapes from blobs into spirals and back.',
    phrasings=('an animated fractal that keeps changing shape',
               'a glowing Julia set slowly melting into new forms',
               'morphing fractal background with swirling spirals'),
    related=('squircle-morph', 'superformula-morph', 'shape-morph', 'letter-morph', 'shape-morph-loader',
             'particle-morph'),
    api=('videobuilder.capabilities.particles.julia_set_morph.draw_julia',
         'videobuilder.capabilities.particles.julia_set_morph.julia_constant',
         'videobuilder.capabilities.particles.julia_set_morph.julia_image'),
    demo=lambda: demo.film(draw),
)
