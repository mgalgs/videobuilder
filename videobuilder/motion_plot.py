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
    elif kind == 3:
        c.move_to(x, y-size); c.line_to(x+size, y); c.line_to(x, y+size); c.line_to(x-size, y); c.close_path()
    else:
        points = {4: (3, math.pi/2), 5: (5, -math.pi/2),
                  6: (6, -math.pi/2), 7: (8, -math.pi/2)}
        count, angle = points[kind % 8]
        for j in range(count):
            radius = size * (.48 if kind % 8 == 7 and j % 2 else 1)
            px = x + radius * math.cos(angle + 2*math.pi*j/count)
            py = y + radius * math.sin(angle + 2*math.pi*j/count)
            if j == 0: c.move_to(px, py)
            else: c.line_to(px, py)
        c.close_path()
    c.fill()


def _label_positions(endpoints, top, bottom, spacing=17):
    """Keep labels near their endpoints without letting them collide or leave the plot."""
    positions = {}
    ordered = sorted(endpoints.items(), key=lambda item: item[1])
    for i, (name, endpoint) in enumerate(ordered):
        positions[name] = max(top, endpoint, positions[ordered[i-1][0]] + spacing if i else top)
    for i in range(len(ordered)-1, -1, -1):
        name = ordered[i][0]
        ceiling = positions[ordered[i+1][0]] - spacing if i+1 < len(ordered) else bottom
        positions[name] = min(positions[name], ceiling)
    return positions


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
    left, right, top, bottom = 74, width - 185, 58, 376
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
        cuts = set(tl.cut_frames())
        for seg in tl.leaves():
            a, z = tl.span(seg)
            if first <= a <= last:
                # Only hard cuts get a solid line; an overlapped segment start is a transition.
                c.set_source_rgb(.45, .45, .45)
                c.set_line_width(1.5 if a in cuts else .8); c.set_dash([] if a in cuts else [3, 3])
                c.move_to(x(a), top); c.line_to(x(a), bottom); c.stroke(); c.set_dash([])
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
    styles = [[], [8, 4], [2, 4], [12, 3, 2, 3],
              [4, 3], [10, 3, 2, 3], [2, 2, 7, 2], [14, 3]]
    endpoints = {name: y(speeds[name][max(speeds[name])]) if speeds[name] else top + 20 + i*17
                 for i, name in enumerate(names)}
    labels = _label_positions(endpoints, top + 12, bottom - 9)
    events = motion_events([{name: tuple(box) for name, box in frames[n].items()}
                            for n in range(first, last+1)])
    for i, name in enumerate(names):
        series = speeds[name]
        grey = .08 + (i % 8)*.075
        c.set_source_rgb(grey, grey, grey)
        c.set_line_width(2.5); c.set_dash(styles[i] if i < len(styles) else [i + 5, 3, 2, 3])
        started = False
        for n in range(first+1, last+1):
            if n not in series:
                if started: c.stroke()
                started = False; continue
            if not started: c.move_to(x(n), y(series[n])); started = True
            else: c.line_to(x(n), y(series[n]))
        if started: c.stroke()
        c.set_dash([])
        stride = max(len(names) + 1, (last-first)//18)
        for n, v in series.items():
            if (n-first-i) % stride == 0:
                _marker(c, i % 8, x(n), y(v))
        for event_name, kind, a, z in events:
            if event_name == name:
                n = first + a + 1
                if n in series:
                    c.set_source_rgb(0, 0, 0)
                    _marker(c, i % 8, x(n), y(series[n]), 7)
                    _text(c, x(n)+5, max(top+13, y(series[n])-11), kind, 10)
        if series:
            n = max(series)
            label_y = labels[name]
            c.set_source_rgb(.6, .6, .6); c.set_line_width(.8); c.set_dash([1, 3])
            c.move_to(x(n), endpoints[name]); c.line_to(right+10, label_y); c.stroke(); c.set_dash([])
            c.set_source_rgb(0, 0, 0)
            _marker(c, i % 8, right+11, label_y)
            _text(c, right+21, label_y+4, name, 12)
        else:
            _marker(c, i % 8, right+11, labels[name])
            _text(c, right+21, labels[name]+4, name, 12)
    c.set_source_rgb(.2, .2, .2)
    _text(c, left, 410, f'f{first}')
    _text(c, right-40, 410, f'f{last}')
    if onion:
        ox, oy = (width-ow)//2, graph_h+20
        c.set_source_rgb(.3, .3, .3)
        _text(c, 20, graph_h+17, f'Onion skin: every {onion} frame(s)', 13)
        chosen = list(range(first, last+1, onion))
        if chosen[-1] != last: chosen.append(last)
        # Frames are opaque, so stacking them would show only the newest. Painting frame i at
        # alpha w_i / (w_0 + ... + w_i) leaves an exact weighted average, newest weighted most.
        total = 0
        for i, n in enumerate(chosen):
            cv = film.frame(n, fmt, scale=scale)
            total += i + 1
            c.set_source_surface(cv.surface, ox, oy)
            c.paint_with_alpha((i + 1) / total)
        for i, name in enumerate(names):
            points = [(ox+box.cx*scale, oy+box.cy*scale)
                      for n in chosen for box in [frames[n].get(name)] if box]
            if not points: continue
            grey = .08 + (i % 8)*.075
            for halo in (True, False):  # a white halo keeps the trail visible on dark films
                c.set_source_rgb(*((1, 1, 1) if halo else (grey, grey, grey)))
                c.set_line_width(5 if halo else 2)
                c.set_dash([] if halo else styles[i] if i < len(styles) else [i + 5, 3, 2, 3])
                c.move_to(*points[0])
                for pt in points[1:]: c.line_to(*pt)
                c.stroke(); c.set_dash([])
                for px, py in points: _marker(c, i%8, px, py, 5 if halo else 3)
    surface.write_to_png(out)
    summary = []
    for name in names:
        series = speeds[name]
        pk_n = max(series, key=series.get) if series else first
        settled = next((n for n in series if all(v <= .5 for k, v in series.items() if k >= n)), None)
        summary.append((name, series.get(pk_n, 0), pk_n, settled))
    return width, height, summary
