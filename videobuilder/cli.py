"""Command line: render, still, sheet, preview.

    python -m videobuilder render  film.py [--format 9x16|16x9|1x1|all] [--jobs N] [--out FILE]
    python -m videobuilder still   film.py FRAME [FRAME ...] [--format F] [--out PATH] [--overlay]
    python -m videobuilder sheet   film.py [--format F] [--every N | --frames 0,30,60] [--out FILE] [--width W] [--cols C]
    python -m videobuilder preview film.py [--port 8000] [--host 127.0.0.1]
"""
import argparse
import os
import sys

from .film import load


def _stem(path):
    return os.path.splitext(os.path.basename(path))[0]


def _formats(film, arg):
    if arg == 'all':
        return list(film.formats)
    return [film.format(arg)]


def cmd_render(a):
    from .render import render
    film = load(a.film)
    fmts = _formats(film, a.format)
    frames = tuple(int(x) for x in a.frames.split(':')) if a.frames else None
    for fmt in fmts:
        out = a.out or f'{_stem(a.film)}-{fmt.name}.mp4'
        if len(fmts) > 1 and a.out:
            root, ext = os.path.splitext(a.out)
            out = f'{root}-{fmt.name}{ext or ".mp4"}'
        render(film, out, fmt, jobs=a.jobs, chunk=a.chunk, crf=a.crf, frames=frames)


def _still(film, n, fmt, overlay=False, scale=1.0):
    if not 0 <= n < film.frames:
        raise SystemExit(f'frame {n} outside 0..{film.frames - 1}')
    cv = film.frame(n, fmt, scale=scale)
    if overlay:
        from . import overlay as ov
        ov.draw(cv, film, n)
    return cv


def cmd_still(a):
    film = load(a.film)
    for fmt in _formats(film, a.format):
        many = len(a.frames) > 1 or a.format == 'all'
        for n in a.frames:
            name = f'{_stem(a.film)}-{fmt.name}-f{n:05d}.png'
            if a.out and many:
                os.makedirs(a.out, exist_ok=True)
                path = os.path.join(a.out, name)
            else:
                path = a.out or name
            _still(film, n, fmt, a.overlay, a.scale).save_png(path)
            print(path)


def sheet_tiles(fmt):
    """Default (thumbnail width, columns) of a sheet in `fmt`: 360 px x 6 for a
    portrait format, 480 px x 4 otherwise, so each format's sheet reads well."""
    return (360, 6) if fmt.portrait else (480, 4)


def contact_sheet(film, frames, fmt, width=None, cols=None, overlay=False, decorate=None):
    """A PIL image: the given frames as thumbnails `width` px wide, labelled.
    `width` and `cols` default to `sheet_tiles(fmt)`.

    `frames` holds frame numbers or (frame, label) pairs; a frame without a
    label is named by its segment. `decorate(canvas, n)`, if given, is called
    on each drawn frame and may draw over it in film px (a check's overlay,
    using `canvas.marks`, say); a string it returns is added to the label.
    """
    from PIL import Image, ImageDraw
    fmt = film.format(fmt)
    dw, dc = sheet_tiles(fmt)
    width, cols = width or dw, cols or dc
    scale = width / fmt.width
    th = round(fmt.height * scale)
    label = 22
    gap = 8
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * (width + gap) + gap, rows * (th + label + gap) + gap), (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    for i, item in enumerate(frames):
        n, name = (item, '') if isinstance(item, int) else item
        cv = _still(film, n, fmt, overlay, scale)
        note = decorate(cv, n) if decorate else None
        cv.surface.flush()
        w, h = cv.surface.get_width(), cv.surface.get_height()
        im = Image.frombuffer('RGBA', (w, h), bytes(cv.surface.get_data()), 'raw', 'BGRA', cv.surface.get_stride(), 1)
        x = gap + (i % cols) * (width + gap)
        y = gap + (i // cols) * (th + label + gap)
        sheet.paste(im.convert('RGB'), (x, y))
        text = f'f {n}  {n / film.fps:.2f}s'
        if not name and film.timeline is not None:
            try:
                name = film.timeline.label(n)
            except IndexError:
                pass
        if name:
            text += f'  {name}'
        if isinstance(note, str):
            text += f'  {note}'
        d.text((x + 2, y + th + 4), text, fill=(220, 220, 220))
    return sheet


def default_sheet_frames(film, every=None):
    """`every` N frames if asked; else the film's keyframes; else the first,
    middle and last frame of each segment, groups' children included (or one a
    second, with no timeline)."""
    if every:
        return list(range(0, film.frames, every))
    if film.keyframes:
        return list(film.keyframes)
    tl = film.timeline
    if tl is None:
        return list(range(0, film.frames, film.fps))
    b = tl.grid.b
    picks = set()
    for s in tl.leaves():
        a, z = b(s.at), b(s.until)
        picks.update((a, (a + z) // 2, z - 1))  # in, middle, last frame of each segment
    return sorted(p for p in picks if 0 <= p < film.frames)


def cmd_sheet(a):
    film = load(a.film)
    frames = [int(x) for x in a.frames.split(',')] if a.frames else default_sheet_frames(film, a.every)
    for fmt in _formats(film, a.format):
        out = a.out or f'{_stem(a.film)}-{fmt.name}-sheet.png'
        if a.format == 'all' and a.out:
            root, ext = os.path.splitext(a.out)
            out = f'{root}-{fmt.name}{ext or ".png"}'
        contact_sheet(film, frames, fmt, a.width, a.cols, a.overlay).save(out)
        print(out)


def cmd_preview(a):
    from .preview import serve
    serve(a.film, host=a.host, port=a.port, open_browser=a.open)


def main(argv=None):
    p = argparse.ArgumentParser(prog='videobuilder', description='Make videos in code.')
    sub = p.add_subparsers(dest='cmd', required=True)

    r = sub.add_parser('render', help='render a film to MP4')
    r.add_argument('film')
    r.add_argument('--format', help="a format name, or 'all' (default: the film's first)")
    r.add_argument('--jobs', type=int, help='worker processes (default: CPU count)')
    r.add_argument('--out', help='output file (default: <film>-<format>.mp4)')
    r.add_argument('--frames', help='a:b, half-open, to render part of the film')
    r.add_argument('--chunk', type=int, default=15, help='frames per encoded chunk')
    r.add_argument('--crf', type=int, default=18, help='x264 quality (lower is better)')
    r.set_defaults(fn=cmd_render)

    s = sub.add_parser('still', help='render frames to PNG')
    s.add_argument('film')
    s.add_argument('frames', type=int, nargs='+', metavar='frame')
    s.add_argument('--format')
    s.add_argument('--out', help='PNG path, or a directory when there are several stills')
    s.add_argument('--overlay', action='store_true', help='draw the timeline overlay')
    s.add_argument('--scale', type=float, default=1.0)
    s.set_defaults(fn=cmd_still)

    c = sub.add_parser('sheet', help="a contact sheet of frames (default: the film's keyframes, or in/middle/out of each segment)")
    c.add_argument('film')
    c.add_argument('--format')
    c.add_argument('--frames', help='comma-separated frame numbers')
    c.add_argument('--every', type=int, help='every N frames')
    c.add_argument('--cols', type=int, help='default: 6 for portrait formats, else 4')
    c.add_argument('--width', type=int, help='thumbnail width, px (default: 360 for portrait formats, else 480)')
    c.add_argument('--overlay', action='store_true')
    c.add_argument('--out')
    c.set_defaults(fn=cmd_sheet)

    v = sub.add_parser('preview', help='serve a live preview with hot reload')
    v.add_argument('film')
    v.add_argument('--host', default='127.0.0.1')
    v.add_argument('--port', type=int, default=8000)
    v.add_argument('--open', action='store_true', help='open a browser')
    v.set_defaults(fn=cmd_preview)

    a = p.parse_args(argv)
    a.fn(a)


def film_main(path, argv=None):
    """Run the CLI on the film file `path`, so a film is runnable on its own:
    end it with `if __name__ == '__main__': videobuilder.main(__file__)`, and
    `python film.py render --format all` is `python -m videobuilder render
    film.py --format all`. `argv` defaults to the command line."""
    argv = sys.argv[1:] if argv is None else list(argv)
    if not argv or argv[0].startswith('-'):
        return main(argv or ['--help'])
    return main([argv[0], os.path.abspath(path), *argv[1:]])
