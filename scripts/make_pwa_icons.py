#!/usr/bin/env python3
"""Draws the home-screen icons (videobuilder/icons/*.png) from the header
mark: the red rounded square with the white play triangle (pages._LOGO).

    python3 scripts/make_pwa_icons.py

Re-run after changing the mark, and commit the PNGs it writes."""
import math
from pathlib import Path

import cairo

RED = (0xe5 / 255, 0x48 / 255, 0x3b / 255)
OUT = Path(__file__).resolve().parent.parent / 'videobuilder' / 'icons'


def _mark(ctx, x, y, size, rounded=True):
    """The 34-unit mark at (x, y), `size` px across."""
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(size / 34, size / 34)
    ctx.set_source_rgb(*RED)
    if rounded:
        r = 9
        ctx.new_sub_path()
        ctx.arc(34 - r, r, r, -math.pi / 2, 0)
        ctx.arc(34 - r, 34 - r, r, 0, math.pi / 2)
        ctx.arc(r, 34 - r, r, math.pi / 2, math.pi)
        ctx.arc(r, r, r, math.pi, 3 * math.pi / 2)
        ctx.close_path()
        ctx.fill()
    else:
        ctx.paint()
    # The logo's triangle, its 1-unit corner arcs drawn as a round-joined stroke.
    ctx.move_to(13.75, 11.2)
    ctx.line_to(13.75, 22.8)
    ctx.line_to(24.9, 17)
    ctx.close_path()
    ctx.set_source_rgb(1, 1, 1)
    ctx.set_line_width(1.5)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.fill_preserve()
    ctx.stroke()
    ctx.restore()


def _write(name, size, draw):
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    draw(cairo.Context(surface), size)
    surface.write_to_png(str(OUT / name))


def main():
    OUT.mkdir(exist_ok=True)
    for size in (192, 512):
        _write(f'icon-{size}.png', size, lambda ctx, s: _mark(ctx, 0, 0, s))
    # iOS rounds the corners itself and turns transparency black, so this one is full-bleed.
    _write('apple-touch-icon.png', 180, lambda ctx, s: _mark(ctx, 0, 0, s, rounded=False))

    def maskable(ctx, s):
        ctx.set_source_rgb(*RED)
        ctx.paint()
        # The whole mark, corners included, fits inside the central 80% circle (the safe zone).
        inner = round(s * 0.8 / math.sqrt(2)) - 8
        _mark(ctx, (s - inner) / 2, (s - inner) / 2, inner)
    _write('icon-maskable-512.png', 512, maskable)


if __name__ == '__main__':
    main()
