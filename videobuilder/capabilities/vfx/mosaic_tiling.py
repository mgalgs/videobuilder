"""Mosaic tiling: a picture rebuilt from small square tiles, each one flat
colour (the average of the patch it covers), set slightly crooked on a dark
grout so it reads as stone or glass laid by hand rather than as pixels."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

GROUT = '#1b1a1f'
_GRIDS = {}  # (image id, cols, rows) -> rows of (r, g, b): one downsample per image and size


def _grid(img, cols, rows):
    key = (id(img), cols, rows)
    if key not in _GRIDS:
        pil = img._pil.convert('RGB').resize((cols, rows), vb.canvas.PILImage.BOX)
        px = pil.load()
        _GRIDS[key] = [[px[c, r] for c in range(cols)] for r in range(rows)]
    return _GRIDS[key]


def _hex(rgb):
    return '#%02x%02x%02x' % tuple(max(0, min(255, round(v))) for v in rgb)


def mosaic(cv, img, x, y, w, h, tile=40, grout=0.12, jitter=0.08, shade=0.1, reveal=None, seed=7,
           grout_color=GROUT):
    """Draw `img` into the box (x, y, w, h) as a mosaic of square tiles about
    `tile` px across, on `grout_color`. Each tile takes its patch's average
    colour, shrunk by `grout` (a share of the tile) for the gaps, nudged and
    shaded by up to `jitter` and `shade` so the rows look hand set; `seed`
    fixes the wobble so it holds still from frame to frame.

    `reveal(col, row, cols, rows) -> 0..1`, when given, scales each tile in
    from nothing (0) to laid (1), for a mosaic that assembles itself;
    `mosaic_sweep(p)` makes a diagonal one."""
    cols, rows = max(1, round(w / tile)), max(1, round(h / tile))
    cw, ch = w / cols, h / rows
    colors = _grid(img, cols, rows)
    rng = random.Random(seed)
    cv.rect(x, y, w, h, grout_color)
    with cv.clip(x, y, w, h):
        for r in range(rows):
            for c in range(cols):
                dx, dy, ds, dl = (rng.uniform(-1, 1) for _ in range(4))
                k = 1.0 if reveal is None else vb.clamp01(reveal(c, r, cols, rows))
                if k <= 0:
                    continue
                s = (1 - grout) * (1 + ds * jitter * 0.5) * k
                tw, th = cw * s, ch * s
                cx = x + (c + 0.5 + dx * jitter) * cw
                cy = y + (r + 0.5 + dy * jitter) * ch
                lit = 1 + dl * shade
                cv.rect(cx - tw / 2, cy - th / 2, tw, th, _hex(v * lit for v in colors[r][c]),
                        radius=min(tw, th) * 0.12)


def mosaic_sweep(p, spread=0.35, ease=vb.ease_out_back):
    """A `reveal` for `mosaic`: tiles set in a diagonal sweep from the top left
    as `p` runs 0 -> 1, each popping in over `spread` of the run."""
    def reveal(c, r, cols, rows):
        at = (c / max(1, cols - 1) + r / max(1, rows - 1)) / 2 * (1 - spread)
        return ease(vb.clamp01((p - at) / spread))
    return reveal


def _draw(n, cv):
    img = demo.photo()
    bw, bh = demo.W * 0.8, demo.H * 0.8
    x, y = (demo.W - bw) / 2, (demo.H - bh) / 2
    p = demo.phase(n, 0.2, 2.2)
    cv.shadow(x, y, bw, bh, radius=4, dy=8, blur=24, color=(0, 0, 0, 0.5))
    mosaic(cv, img, x, y, bw, bh, tile=bw / 40, reveal=mosaic_sweep(p))


CAPABILITY = Capability(
    id='mosaic-tiling',
    name='Mosaic tiling',
    family='vfx',
    group='Pixel & mosaic',
    aliases=('tile mosaic', 'tesserae', 'mosaic filter', 'tiled mosaic effect'),
    definition='A picture is rebuilt out of small, slightly uneven square tiles, each a single colour '
               'taken from the patch beneath it, set in dark grout like stone or glass.',
    phrasings=('make the photo look like it was laid out in little tiles',
               'turn this image into a tile mosaic that builds itself',
               'a Roman-floor mosaic version of the shot'),
    related=('pattern-tiling', 'tessellation-triangle-flip', 'truchet-tiles', 'penrose-tiling',
             'pixelate-transition', 'scale-tile-wave'),
    api=('videobuilder.capabilities.vfx.mosaic_tiling.mosaic',
         'videobuilder.capabilities.vfx.mosaic_tiling.mosaic_sweep'),
    demo=lambda: demo.film(_draw),
)
