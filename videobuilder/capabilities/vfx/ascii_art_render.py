"""ASCII art render: a picture redrawn as a grid of monospaced characters,
each cell's glyph picked by how bright the image is there (dense glyphs for
light, sparse ones for dark), optionally tinted with the image's own colour."""
from PIL import ImageOps

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ..typography.ascii_glyph_density_reveal import RAMP, draw_density


def luminance_grid(img, cols, rows, invert=False, contrast=1.0):
    """The brightness of the image `img` (a `vb.Image` or a PIL image) over a
    `cols` x `rows` grid of cells: a list of rows of 0 -> 1, each cell the
    average of its block of the source, levels stretched so the darkest
    cell is 0 and the brightest 1. `invert` for dark ink on a light ground;
    `contrast` > 1 pushes values away from mid-grey. Compute it once and
    reuse it every frame."""
    pil = ImageOps.autocontrast(getattr(img, '_pil', img).convert('L').resize((max(1, cols), max(1, rows))))
    grid = []
    for r in range(rows):
        row = []
        for c in range(cols):
            v = pil.getpixel((c, r)) / 255
            v = vb.clamp01(0.5 + (v - 0.5) * contrast)
            row.append(1 - v if invert else v)
        grid.append(row)
    return grid


def draw_ascii(cv, grid, font, x, y, cell_w, cell_h, color=None, img=None, ramp=RAMP, dim=None, lift=0.3):
    """Draw a brightness `grid` (from `luminance_grid`) from its top-left
    (x, y) as glyphs from `ramp`, densest last, one `cell_w` x `cell_h` cell
    per value. With `img`, each glyph takes the colour of the image under it
    (the image laid over the grid's box, seen only through the glyphs,
    lightened `lift` of the way to white so dark areas stay legible);
    otherwise every glyph is `color` (default the demo ink), sparse ones
    fading towards `dim`. Returns the grid's Box."""
    rows, cols = len(grid), len(grid[0]) if grid else 0
    box = vb.Box(x, y, cols * cell_w, rows * cell_h)
    if img is None:
        return draw_density(cv, grid, font, x, y, cell_w, cell_h, color or demo.INK, dim=dim, ramp=ramp)
    ctx = cv.ctx
    ctx.push_group()
    cv.image(img, *box)
    if lift:
        cv.rect(*box, '#ffffff', alpha=lift)
    source = ctx.pop_group()
    ctx.push_group()
    draw_density(cv, grid, font, x, y, cell_w, cell_h, '#ffffff', ramp=ramp)
    glyphs = ctx.pop_group()
    ctx.save()
    ctx.set_source(source)
    ctx.mask(glyphs)
    ctx.restore()
    return box


def ascii_render(cv, img, x, y, w, h, font, p=1.0, color=None, tinted=True, contrast=1.0, ramp=RAMP):
    """`img` laid into the box (x, y, w, h) and turned into ASCII art, the
    conversion sweeping left to right with progress `p` (0: the plain image,
    1: all characters). Cells are one glyph of `font` wide and one line
    tall. `tinted` keeps the image's colours on the glyphs; otherwise they
    are `color`. Returns the box."""
    cell_w, cell_h = vb.text.measure('@', font), vb.text.line_height(font)
    cols, rows = max(1, int(w // cell_w)), max(1, int(h // cell_h))
    key = (id(img), cols, rows, contrast)
    if _cache.get('key') != key:
        _cache.update(key=key, grid=luminance_grid(img, cols, rows, contrast=contrast))
    grid = _cache['grid']
    gx, gy = x + (w - cols * cell_w) / 2, y + (h - rows * cell_h) / 2
    edge = gx + cols * cell_w * vb.clamp01(p)
    if p < 1:
        with cv.clip(edge, y, x + w - edge, h):
            cv.image(img, x, y, w, h)
    if p > 0:
        with cv.clip(gx, y, edge - gx, h):
            draw_ascii(cv, grid, font, gx, gy, cell_w, cell_h, color=color, img=img if tinted else None,
                       ramp=ramp)
        if p < 1:
            cv.line(edge, y, edge, y + h, demo.INK, width=2, alpha=0.8)
    return vb.Box(x, y, w, h)


_cache = {}
FONT = demo.mono(12, 700)


def draw(n, cv):
    img = demo.photo()
    w = 780
    h = w * img.h / img.w
    box = ascii_render(cv, img, (demo.W - w) / 2, (demo.H - h) / 2, w, h, FONT,
                       p=vb.ease_in_out_quart(demo.phase(n, 0.5, 2.1)))
    cv.mark('image', *box)


CAPABILITY = Capability(
    id='ascii-art-render',
    name='ASCII art render',
    family='vfx',
    group='Pixel & mosaic',
    aliases=('ASCII filter', 'text-mode image', 'character art effect', 'ASCII shader'),
    definition='An image is rebuilt from rows of typed characters, with heavy symbols standing in for its '
               'bright areas and light dots or blanks for its dark ones.',
    phrasings=('turn the photo into ASCII art made of letters and symbols',
               'make the footage look like it is drawn with old terminal characters',
               'redraw the picture using text characters instead of pixels'),
    related=('ascii-glyph-density-reveal', 'pixel-sort-text', 'dot-matrix-text', 'per-character-fade-in',
             'symbol-to-letter-decode', 'pixelation-reveal'),
    api=('videobuilder.capabilities.vfx.ascii_art_render.ascii_render',
         'videobuilder.capabilities.vfx.ascii_art_render.draw_ascii',
         'videobuilder.capabilities.vfx.ascii_art_render.luminance_grid',
         'videobuilder.capabilities.typography.ascii_glyph_density_reveal.draw_density'),
    demo=lambda: demo.film(draw),
)
