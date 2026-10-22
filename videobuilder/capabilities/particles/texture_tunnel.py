"""Texture tunnel: a repeating texture wrapped round the inside of an endless
tube seen from within, streaming towards the camera out of a dark vanishing
point while the tube turns and its mouth drifts about the frame.

It is the old per-pixel remap: every screen pixel looks up the texture at
(its angle round the centre, depth / its distance from the centre), so
moving through the tube is just adding an offset to the lookup. The lookup
table is made once for a field twice the picture's size and a window of it
is read each frame, so the mouth can wander without rebuilding it. Pillow
only, no numpy, at a small working size the canvas scales up.
"""
import math
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw, ImageFilter

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

TEX = 128          # texture side, a power of two so lookups wrap with a mask
SHIFT = 7          # log2(TEX)
MASK = TEX - 1
FIRE = ((0.0, (12, 4, 10)), (0.3, (120, 16, 24)), (0.55, (239, 91, 76)),
        (0.78, (255, 170, 60)), (1.0, (255, 240, 190)))


def _ramp(stops, t):
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            k = (t - t0) / (t1 - t0)
            return tuple(round(a + (b - a) * k) for a, b in zip(c0, c1))
    return stops[-1][1]


@lru_cache(maxsize=4)
def plasma_texture(seed=0, palette=FIRE, seams=4):
    """A tileable 128 x 128 fire-coloured plasma as a PIL RGB image, with
    `seams` dark grid lines each way so the motion through the tube reads.
    Every wave has a whole number of periods across the tile, so it wraps
    without a join. The same `seed` gives the same texture."""
    tau = 2 * math.pi / TEX
    ph = [(seed * 1.7 + i * 2.3) % (2 * math.pi) for i in range(4)]
    px = []
    for y in range(TEX):
        for x in range(TEX):
            v = (math.sin(x * tau * 2 + ph[0]) + math.sin(y * tau * 3 + ph[1])
                 + math.sin((x + y) * tau * 2 + ph[2]) + math.sin((x - 2 * y) * tau + ph[3]))
            px.append(_ramp(palette, min(1.0, max(0.0, 0.5 + v / 5))))
    im = Image.new('RGB', (TEX, TEX))
    im.putdata(px)
    if seams:
        lines = Image.new('L', (TEX, TEX), 255)
        d = ImageDraw.Draw(lines)
        step = TEX // seams
        for k in range(seams):
            d.line((k * step, 0, k * step, TEX), fill=60, width=2)
            d.line((0, k * step, TEX, k * step), fill=60, width=2)
        lines = lines.filter(ImageFilter.GaussianBlur(0.8))
        im = ImageChops.multiply(im, Image.merge('RGB', (lines,) * 3))
    return im


@lru_cache(maxsize=4)
def _field(w, h, depth, wraps):
    """Rows of (u, v) texture coordinates for a 2w x 2h field centred on
    (w, h), and the matching fog image (dark at the centre, clear at the rim)."""
    rows = []
    fog = []
    reach = math.hypot(w, h) / 2
    for y in range(2 * h):
        dy = y - h + 0.5
        row = []
        for x in range(2 * w):
            dx = x - w + 0.5
            r = math.hypot(dx, dy)
            u = int((math.atan2(dy, dx) / (2 * math.pi) + 1) * TEX * wraps)
            v = int(depth * TEX / r)
            row.append((u, v))
            fog.append(round(255 * min(1.0, (r / reach) ** 1.4)))
        rows.append(row)
    shade = Image.new('L', (2 * w, 2 * h))
    shade.putdata(fog)
    return rows, Image.merge('RGB', (shade,) * 3)


def tunnel_image(texture, size, travel, spin=0.0, center=(0.5, 0.5), depth=0.6, wraps=4, fog=True):
    """One frame of a texture tunnel as a PIL RGB image of `size` (w, h).

    `texture`: a PIL image, resampled to 128 x 128 and tiled. `travel`: how
    far down the tube, in texture tiles (animate it upwards to fly in).
    `spin`: turns of the tube about its axis. `center`: where the vanishing
    point sits, as a fraction of the frame, within a quarter of the edges.
    `depth`: the tube's radius as a fraction of the frame's width; larger
    packs more rings of texture on screen. `wraps`: texture repeats round the circumference.
    `fog`: darken towards the vanishing point."""
    w, h = size
    tex = texture.convert('RGB')
    if tex.size != (TEX, TEX):
        tex = tex.resize((TEX, TEX), Image.LANCZOS)
    raw = tex.tobytes()
    cells = [raw[i:i + 3] for i in range(0, len(raw), 3)]
    rows, shade = _field(w, h, depth * w, wraps)
    cx = min(max(center[0], 0.25), 0.75)
    cy = min(max(center[1], 0.25), 0.75)
    x0, y0 = round(w * (1 - cx)), round(h * (1 - cy))
    ou = round(spin * TEX * wraps)
    ov = round(travel * TEX)
    out = b''.join(cells[((v + ov) & MASK) << SHIFT | ((u + ou) & MASK)]
                   for row in rows[y0:y0 + h] for u, v in row[x0:x0 + w])
    im = Image.frombytes('RGB', (w, h), out)
    if fog:
        im = ImageChops.multiply(im, shade.crop((x0, y0, x0 + w, y0 + h)))
    return im


def draw_tunnel(cv, texture, travel, spin=0.0, center=(0.5, 0.5), box=None, res=384, **kw):
    """Draw a texture tunnel filling `box` (x, y, w, h; default the whole
    canvas), worked out `res` pixels wide and scaled up smoothly. `kw` goes
    to `tunnel_image`. Returns the Box drawn."""
    x, y, w, h = box or (0, 0, cv.width, cv.height)
    size = (res, max(2, round(res * h / w)))
    img = vb.Image.from_pil(tunnel_image(texture, size, travel, spin, center, **kw))
    cv.image(img, x, y, w, h)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    t = n / demo.FPS
    travel = 1.6 * t + 0.25 * t * t            # flying in, picking up speed
    spin = 0.06 * t
    center = (0.5 + 0.12 * math.sin(t * 1.9), 0.5 + 0.1 * math.sin(t * 1.3 + 0.6))
    box = draw_tunnel(cv, plasma_texture(), travel, spin, center)
    cv.mark('tunnel', *box)


TECHNIQUE = Technique(
    id='texture-tunnel',
    name='Texture tunnel',
    family='particles',
    group='Fire & plasma',
    aliases=('demoscene tunnel', 'tunnel effect', 'warp tunnel', 'wormhole'),
    definition='A tiled texture lines the inside of an endless tube that the camera rushes down, '
               'the pattern pouring out of a dark point in the middle and sweeping past the edges.',
    phrasings=('fly down a glowing tunnel made of a repeating pattern',
               'an old-school demo tunnel with fire streaming towards us',
               'zoom through a wormhole lined with plasma'),
    related=('perspective-tunnel-type', 'infinite-zoom-tunnel', 'liquify', 'zoom-through-shape',
             'elastic-stretch', 'parallax-slide'),
    api=('videobuilder.techniques.particles.texture_tunnel.draw_tunnel',
         'videobuilder.techniques.particles.texture_tunnel.tunnel_image',
         'videobuilder.techniques.particles.texture_tunnel.plasma_texture'),
    demo=lambda: demo.film(draw),
)
