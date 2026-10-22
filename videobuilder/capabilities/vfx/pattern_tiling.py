"""Pattern tiling: one small motif drawn once, then stamped cell after cell
across the plane -- shifted, mirrored or turned by a wallpaper-group rule --
so it reads as a single seamless repeating pattern, like wallpaper or a
textile print."""
import math

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Capability

SYMMETRIES = ('translate', 'mirror', 'rotate', 'brick')
_QUARTERS = ((0, 1), (3, 2))  # quarter turns per cell of a 2x2 block, going round it


def _cell_transform(c, size, i, j, symmetry):
    """Apply, about a cell's own centre, the flip or turn the rule gives cell (i, j)."""
    h = size / 2
    if symmetry == 'mirror':
        c.translate(h, h)
        c.scale(-1 if i % 2 else 1, -1 if j % 2 else 1)
        c.translate(-h, -h)
    elif symmetry == 'rotate':
        c.translate(h, h)
        c.rotate(_QUARTERS[j % 2][i % 2] * math.pi / 2)
        c.translate(-h, -h)


def pattern_tile(cv, motif, size=120, symmetry='mirror', box=None, offset=(0.0, 0.0), reveal=None):
    """Fill `box` (default the whole canvas) with `motif` repeated on a grid of
    `size`-px square cells. `motif(cv, size)` draws one cell in local
    coordinates 0..size, 0..size. `symmetry` picks how each copy is placed:
    'translate' (plain repeat), 'mirror' (neighbours flip, so edges meet in
    reflections), 'rotate' (each 2x2 block turns the motif through four
    quarter turns) or 'brick' (every other row shifted half a cell).
    `offset` (x, y) slides the whole pattern; the repeat is seamless, so
    animating it pans endlessly. `reveal(i, j)` -> 0..1, if given, scales and
    fades the cell at grid index (i, j) in about its centre; index (0, 0) is
    the cell whose corner sits at `offset`. Returns the cell size."""
    if symmetry not in SYMMETRIES:
        raise ValueError(f'symmetry must be one of {", ".join(SYMMETRIES)}, not {symmetry!r}')
    x, y, w, h = box if box is not None else (0, 0, cv.width, cv.height)
    ox, oy = offset
    c = cv.ctx
    c.save()
    c.rectangle(x, y, w, h)
    c.clip()
    j0, j1 = math.floor((y - oy) / size) - 1, math.ceil((y + h - oy) / size) + 1
    for j in range(j0, j1):
        shift = size / 2 if symmetry == 'brick' and j % 2 else 0.0
        i0, i1 = math.floor((x - ox - shift) / size) - 1, math.ceil((x + w - ox - shift) / size) + 1
        for i in range(i0, i1):
            k = 1.0 if reveal is None else vb.clamp01(reveal(i, j))
            if k <= 0:
                continue
            c.save()
            c.translate(ox + shift + i * size, oy + j * size)
            if k < 1:
                c.translate(size / 2, size / 2)
                c.scale(k, k)
                c.translate(-size / 2, -size / 2)
            _cell_transform(c, size, i, j, symmetry)
            with cv.layer(opacity=k):
                motif(cv, size)
            c.restore()
    c.restore()
    return size


def leaf_motif(cv, size, ink=demo.ACCENT, second=demo.TEAL, line=demo.INK):
    """A deliberately lopsided motif (a corner quarter-disc, a leaf, a dot and
    a bar), so the flips and turns of each copy are easy to see."""
    s = size
    cv.sector(0, 0, s * 0.42, 0, math.pi / 2, ink)
    c = cv.ctx
    c.new_path()
    c.move_to(s * 0.98, s * 0.98)
    c.curve_to(s * 0.95, s * 0.5, s * 0.6, s * 0.3, s * 0.36, s * 0.36)
    c.curve_to(s * 0.4, s * 0.62, s * 0.55, s * 0.92, s * 0.98, s * 0.98)
    c.close_path()
    c.set_source_rgba(*rgba(second))
    c.fill()
    demo.dot(cv, s * 0.8, s * 0.22, r=s * 0.08, color=line)
    cv.rect(s * 0.1, s * 0.82, s * 0.32, s * 0.06, line, radius=s * 0.03, alpha=0.8)


SIZE = 135


def draw(n, cv):
    # The seed cell sits in the middle of the frame; copies spread out ring by ring,
    # then the finished pattern drifts diagonally to show it repeats without seams.
    drift = demo.phase(n, 1.9, 3.0)
    pan = SIZE * 1.2 * vb.ease_in_out_quart(drift)
    ox = demo.W / 2 - SIZE / 2 + pan
    oy = demo.H / 2 - SIZE / 2 + pan * 0.5
    spread = demo.phase(n, 0.55, 1.8)

    def reveal(i, j):
        ring = max(abs(i), abs(j))
        if ring == 0:
            return vb.ease_out_back(demo.phase(n, 0.0, 0.45))
        start = (ring - 1) / 6
        return vb.ease_out_back(vb.clamp01((spread - start) / 0.25))

    pattern_tile(cv, leaf_motif, SIZE, 'mirror', offset=(ox, oy), reveal=reveal)
    # Outline the original cell until the copies have filled the frame.
    edge = 1 - demo.phase(n, 1.6, 2.1)
    if edge > 0:
        cv.outline(ox, oy, SIZE, SIZE, demo.INK, width=5, alpha=edge)


CAPABILITY = Capability(
    id='pattern-tiling',
    name='Pattern tiling',
    family='vfx',
    group='Symmetry & geometry',
    aliases=('seamless pattern', 'wallpaper pattern', 'repeat pattern', 'tessellated motif',
             'wallpaper group symmetry'),
    definition='A single small design is copied over and over in a grid, each copy shifted, flipped or '
               'turned, until the frame is covered by one continuous repeating pattern.',
    phrasings=('take this little motif and repeat it across the whole screen like wallpaper',
               'make a seamless tiled pattern background that slowly scrolls',
               'mirror one tile in every direction so it builds a kaleidoscope-like print'),
    related=('mosaic-tiling', 'penrose-tiling', 'truchet-tiles', 'wave-function-collapse', 'pixelation',
             'seamless-loop'),
    api=('videobuilder.capabilities.vfx.pattern_tiling.pattern_tile',
         'videobuilder.capabilities.vfx.pattern_tiling.leaf_motif'),
    demo=lambda: demo.film(draw),
)
