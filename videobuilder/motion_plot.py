"""A monochrome speed chart and optional onion skin for marked boxes."""
import math

import cairo

from .motion import motion_events, sample, speed


def _text(c, x, y, label, size=13):
    c.select_font_face('Sans', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    c.set_font_size(size)
    c.move_to(x, y)
    c.show_text(str(label))


def _marker(c, kind, x, y, size=4):
    c.new_path()
    if kind == 0:
        c.arc(x, y, size, 0, 2 * math.pi)
    elif kind == 1:
        c.rectangle(x-size, y-size, 2*size, 2*size)
    elif kind == 2:
        c.move_to(x, y-size); c.line_to(x+size, y+size); c.line_to(x-size, y+size); c.close_path()
    else:
        c.move_to(x, y-size); c.line_to(x+size, y); c.line_to(x, y+size); c.line_to(x-size, y); c.close_path()
    c.fill()


def render(film, fmt, first, last, marks=None, onion=None, out='motion.png'):
    if not 0 <= first <= last < film.frames:
        raise ValueError(f'frame range must lie in 0..{film.frames - 1}')
    if onion is not None and onion < 1:
        raise ValueError('--onion must be positive')
    frames = sample(film, fmt, range(first, last + 1))
    names = list(dict.fromkeys(name for ms in frames.values() for name in ms))
    if marks:
        unknown = set(marks) - set(names)
        if unknown:
            raise ValueError(f'no samples for marks: {", ".join(sorted(unknown))}')
        names = list(dict.fromkeys(marks))
    width, graph_h = 1100, 440
    scale = min(760 / fmt.width, 500 / fmt.height) if onion else 0
    ow, oh = round(fmt.width * scale), round(fmt.height * scale)
    height = graph_h + (oh + 38 if onion else 0)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    c = cairo.Context(surface)
    c.set_source_rgb(1, 1, 1); c.paint()
    left, right, top, bottom = 74, width - 185, 46, 376
    speeds = {name: {n: speed(frames[n-1][name], frames[n][name])
                     for n in range(first + 1, last + 1)
                     if name in frames[n-1] and name in frames[n]}
              for name in names}
    peak = max((v for series in speeds.values() for v in series.values()), default=0)
    max_y = max(1, peak * 1.12)
    x = lambda n: left + (n-first) * (right-left) / max(1, last-first)
    y = lambda v: bottom - v * (bottom-top) / max_y
    c.set_source_rgb(.3, .3, .3)
    _text(c, 22, 24, f'{fmt.name}  frames {first}-{last}   speed (px/frame)', 17)
    tl = film.timeline
    if tl:
        for seg in tl.leaves():
            a, z = tl.span(seg)
            if first <= a <= last:
                c.set_source_rgb(.45, .45, .45); c.set_line_width(1.5)
                c.move_to(x(a), top); c.line_to(x(a), bottom); c.stroke()
                _text(c, x(a)+3, top-13, seg.name, 12)
        beat = tl.grid.frames_per_beat
        for k in range(math.ceil(first / beat), math.floor(last / beat)+1):
            n = tl.grid.b(k)
            if first <= n <= last:
                c.set_source_rgb(.83, .83, .83); c.set_line_width(.7)
                c.move_to(x(n), bottom); c.line_to(x(n), bottom+6); c.stroke()
    for i in range(5):
        v = max_y * i / 4
        c.set_source_rgb(.88, .88, .88); c.set_line_width(.7)
        c.move_to(left, y(v)); c.line_to(right, y(v)); c.stroke()
        c.set_source_rgb(.25, .25, .25); _text(c, 7, y(v)+4, f'{v:.1f}', 11)
    styles = [[], [8, 4], [2, 4], [12, 3, 2, 3]]
    events = motion_events([{name: tuple(box) for name, box in frames[n].items()}
                            for n in range(first, last+1)])
    for i, name in enumerate(names):
        series = speeds[name]
        c.set_source_rgb(.08 + (i % 4)*.16, .08 + (i % 4)*.16, .08 + (i % 4)*.16)
        c.set_line_width(2.5); c.set_dash(styles[i % len(styles)])
        started = False
        for n in range(first+1, last+1):
            if n not in series:
                if started: c.stroke()
                started = False; continue
            if not started: c.move_to(x(n), y(series[n])); started = True
            else: c.line_to(x(n), y(series[n]))
        if started: c.stroke()
        c.set_dash([])
        stride = max(1, (last-first)//18)
        for n, v in series.items():
            if (n-first) % stride == 0 or n == max(series):
                _marker(c, i % 4, x(n), y(v))
        for event_name, kind, a, z in events:
            if event_name == name:
                n = first + a + 1
                if n in series:
                    c.set_source_rgb(0, 0, 0)
                    _marker(c, i % 4, x(n), y(series[n]), 7)
                    _text(c, x(n)+5, max(top+13, y(series[n])-11), kind, 10)
        if series:
            n = max(series)
            c.set_source_rgb(0, 0, 0)
            _marker(c, i % 4, right+11, y(series[n])+i*15)
            _text(c, right+21, y(series[n])+i*15+4, name, 12)
        else:
            _marker(c, i % 4, right+11, top+20+i*18)
            _text(c, right+21, top+24+i*18, name, 12)
    c.set_source_rgb(.2, .2, .2)
    _text(c, left, 410, f'f{first}')
    _text(c, right-40, 410, f'f{last}')
    if onion:
        ox, oy = (width-ow)//2, graph_h+20
        c.set_source_rgb(.3, .3, .3)
        _text(c, 20, graph_h+17, f'Onion skin: every {onion} frame(s)', 13)
        chosen = list(range(first, last+1, onion))
        if chosen[-1] != last: chosen.append(last)
        for i, n in enumerate(chosen):
            cv = film.frame(n, fmt, scale=scale)
            c.set_source_surface(cv.surface, ox, oy)
            c.paint_with_alpha(.16 + .64*(i+1)/len(chosen))
        for i, name in enumerate(names):
            points = [(ox+box.cx*scale, oy+box.cy*scale)
                      for n in chosen for box in [frames[n].get(name)] if box]
            if not points: continue
            c.set_source_rgb(.04 + (i%4)*.17, .04 + (i%4)*.17, .04 + (i%4)*.17)
            c.set_line_width(2); c.set_dash(styles[i%4])
            c.move_to(*points[0])
            for pt in points[1:]: c.line_to(*pt)
            c.stroke(); c.set_dash([])
            for px, py in points: _marker(c, i%4, px, py, 3)
    surface.write_to_png(out)
    summary = []
    for name in names:
        series = speeds[name]
        pk_n = max(series, key=series.get) if series else first
        settled = next((n for n in series if all(v <= .5 for k, v in series.items() if k >= n)), None)
        summary.append((name, series.get(pk_n, 0), pk_n, settled))
    return width, height, summary
