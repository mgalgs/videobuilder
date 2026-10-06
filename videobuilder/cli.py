"""Command line: render, still, sheet, preview.

    python -m videobuilder render  film.py [--format 9x16|16x9|1x1|all] [--jobs N] [--out FILE]
    python -m videobuilder still   film.py FRAME [FRAME ...] [--format F] [--out PATH] [--overlay]
    python -m videobuilder sheet   film.py [--format F] [--every N | --frames 0,30,60] [--out FILE]
    python -m videobuilder preview film.py [--port 8000] [--host 127.0.0.1]
"""
import argparse
import os

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


def contact_sheet(film, frames, fmt, width=360, cols=6, overlay=False):
    """A PIL image: the given frames as thumbnails `width` px wide, labelled."""
    from PIL import Image, ImageDraw
    fmt = film.format(fmt)
    scale = width / fmt.width
    th = round(fmt.height * scale)
    label = 22
    gap = 8
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * (width + gap) + gap, rows * (th + label + gap) + gap), (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    for i, n in enumerate(frames):
        cv = _still(film, n, fmt, overlay, scale)
        cv.surface.flush()
        w, h = cv.surface.get_width(), cv.surface.get_height()
        im = Image.frombuffer('RGBA', (w, h), bytes(cv.surface.get_data()), 'raw', 'BGRA', cv.surface.get_stride(), 1)
        x = gap + (i % cols) * (width + gap)
        y = gap + (i // cols) * (th + label + gap)
        sheet.paste(im.convert('RGB'), (x, y))
        text = f'f {n}  {n / film.fps:.2f}s'
        if film.timeline is not None:
            try:
                text += f'  {film.timeline.at(n)[0].name}'
            except IndexError:
                pass
        d.text((x + 2, y + th + 4), text, fill=(220, 220, 220))
    return sheet


def default_sheet_frames(film, every=None):
    if every:
        return list(range(0, film.frames, every))
    tl = film.timeline
    if tl is None:
        return list(range(0, film.frames, film.fps))
    b = tl.grid.b
    picks = set()
    for s in tl.segments:
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

    c = sub.add_parser('sheet', help='a contact sheet of frames (default: in/middle/out of each segment)')
    c.add_argument('film')
    c.add_argument('--format')
    c.add_argument('--frames', help='comma-separated frame numbers')
    c.add_argument('--every', type=int, help='every N frames')
    c.add_argument('--cols', type=int, default=6)
    c.add_argument('--width', type=int, default=360, help='thumbnail width, px')
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
