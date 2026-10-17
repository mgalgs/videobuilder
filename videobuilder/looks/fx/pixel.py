"""8-bit pixel filter: the picture shrunk to a chunky grid and mapped to a
16-colour game palette, scaled back up hard-edged, on faint
scan lines. A rolling bar, a tinted band whose rows slip a block sideways,
steps down the screen at 8 fps; draw the picture underneath at
`FILTER.step(t)` and it steps with it.

Options: `block` -- the size of one pixel in film px at 1080 (12)."""
import math

from PIL import Image, ImageChops

from . import Filter, palette_image, posterize

# the PICO-8 palette: sixteen colours an old game would know
COLOURS = ('#000000', '#1d2b53', '#7e2553', '#008751', '#ab5236', '#5f574f', '#c2c3c7', '#fff1e8',
           '#ff004d', '#ffa300', '#ffec27', '#00e436', '#29adff', '#83769c', '#ff77a8', '#ffccaa')
_PALETTE = palette_image(COLOURS)
FPS = 8
ROLL = 2.25        # seconds for the bar to roll down the screen
BAR = 0.24         # the bar's height, a share of the frame


def treat(im, t, age, u, block=12):
    w, h = im.size
    size = max(2.0, block * u)
    gw, gh = max(1, math.ceil(w / size)), max(1, math.ceil(h / size))
    grid = im.resize((gw, gh), Image.BOX)
    grid = posterize(grid, _PALETTE).convert('RGB')
    ts = math.floor(t * FPS + 1e-9) / FPS
    top = int(((ts / ROLL) % 1.0) * (gh + BAR * gh) - BAR * gh)
    bar = max(1, int(BAR * gh))
    a, b = max(0, top), min(gh, top + bar)
    if b > a:                                     # the rolling bar: rows slip a block, tinted blue
        band = grid.crop((0, a, gw, b))
        band = ImageChops.offset(band, 1 if int(ts * FPS) % 2 else -1, 0)
        band = ImageChops.multiply(band, Image.new('RGB', band.size, (170, 180, 255)))
        grid.paste(band, (0, a))
    out = grid.resize((round(gw * size), round(gh * size)), Image.NEAREST).crop((0, 0, w, h))
    lines = _scanlines(w, h, size)
    return ImageChops.multiply(out, lines)


_LINES = {}


def _scanlines(w, h, size):
    key = (w, h, round(size, 2))
    if key not in _LINES:
        row = Image.new('RGB', (1, h), (255, 255, 255))
        px = row.load()
        step = max(2, int(size / 2))
        for y in range(h):
            if y % step == step - 1:
                px[0, y] = (214, 214, 222)
        _LINES.clear()
        _LINES[key] = row.resize((w, h), Image.NEAREST)
    return _LINES[key]


FILTER = Filter('pixel', '8-bit pixel filter', 'chunky pixels, a rolling bar, stepped at 8 fps', treat,
                aliases=('pixel-art layer',), fps=FPS)
