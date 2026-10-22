"""Scatter Time Playback: a scatter plot whose bubbles travel and swell as a
time variable plays forward, each dragging a fading trail of where it has
been, with the current period shown large and a scrubber along the bottom."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _catmull(a, b, c, d, u):
    """The Catmull-Rom curve through b and c (a and d are their neighbours) at `u`."""
    return 0.5 * (2 * b + (c - a) * u + (2 * a - 5 * b + 4 * c - d) * u * u + (3 * b - a - 3 * c + d) * u ** 3)


def sample(keys, t):
    """Smoothly interpolate `keys`, a list of equal-length tuples (x, y, size,
    ...) at evenly spaced times, at `t` (0 -> 1 across the whole list). The
    curve passes through every key, so a point never stops dead at one."""
    t = vb.clamp01(t)
    if len(keys) == 1:
        return tuple(keys[0])
    s = t * (len(keys) - 1)
    i = min(int(s), len(keys) - 2)
    u = s - i
    a, b, c, d = (keys[max(0, min(len(keys) - 1, j))] for j in (i - 1, i, i + 1, i + 2))
    return tuple(_catmull(*v, u) for v in zip(a, b, c, d))


def draw_scatter_playback(cv, box, series, t, x_range=(0, 100), y_range=(0, 100), periods=(2000, 2020),
                          trail=0.35, max_radius=24, grid=5, font=None, label_font=None,
                          ink=demo.INK, muted=demo.MUTED, line=demo.LINE):
    """Draw a scatter plot inside `box` (a `vb.Box`) at playback time `t`
    (0 -> 1). `series` is a list of `(label, color, keys)`; `keys` are
    `(x, y, size)` data points at evenly spaced times (see `sample`), `size`
    0 -> 1 of `max_radius`. Each point leaves a trail covering the last
    `trail` of the timeline, fading out behind it. The period, from
    `periods` (start, end), is printed top-right and marked on a scrubber
    under the plot. Returns the plot's Box."""
    x0, x1 = x_range
    y0, y1 = y_range
    font = font or demo.font(34, 800)
    label_font = label_font or demo.mono(12, 700)

    def to_px(x, y):
        return (box.x + (x - x0) / (x1 - x0) * box.w, box.y + box.h - (y - y0) / (y1 - y0) * box.h)

    for k in range(grid + 1):
        gx, gy = box.x + box.w * k / grid, box.y + box.h * k / grid
        cv.line(gx, box.y, gx, box.y + box.h, line, width=1, alpha=0.6)
        cv.line(box.x, gy, box.x + box.w, gy, line, width=1, alpha=0.6)
        for text, (cx, cy) in ((f'{x0 + (x1 - x0) * k / grid:g}', (gx, box.y + box.h + 14)),
                               (f'{y1 - (y1 - y0) * k / grid:g}', (box.x - 18, gy))):
            w, h = vb.text.block_size([text], label_font)
            vb.text.draw(cv, [text], label_font, cx - w / 2, cy - h / 2, muted)
    cv.line(box.x, box.y + box.h, box.x + box.w, box.y + box.h, muted, width=1.5)
    cv.line(box.x, box.y, box.x, box.y + box.h, muted, width=1.5)

    t = vb.clamp01(t)
    steps = 40
    for label, color, keys in series:
        start = max(0.0, t - trail)
        prev = None
        for j in range(steps + 1):
            tj = start + (t - start) * j / steps
            pt = to_px(*sample(keys, tj)[:2])
            if prev is not None:
                cv.line(*prev, *pt, color, width=3, alpha=0.8 * j / steps)
            prev = pt
    for label, color, keys in sorted(series, key=lambda s: -sample(s[2], t)[2]):
        x, y, size = sample(keys, t)[:3]
        cx, cy = to_px(x, y)
        r = max(4.0, max_radius * size)
        demo.dot(cv, cx, cy, r, color)
        cv.arc(cx, cy, r, 0, 6.2832, ink, width=1.2, alpha=0.35)
        w, h = vb.text.block_size([label], label_font)
        vb.text.draw(cv, [label], label_font, cx - w / 2, cy - h / 2, demo.BG)

    a, b = periods
    now = f'{a + (b - a) * t:.1f}'
    w, h = vb.text.block_size([now], font)
    vb.text.draw(cv, [now], font, box.x + box.w - w, box.y - h - 8, ink)

    sy = box.y + box.h + 44
    cv.line(box.x, sy, box.x + box.w, sy, line, width=3)
    cv.line(box.x, sy, box.x + box.w * t, sy, demo.TEAL, width=3)
    demo.dot(cv, box.x + box.w * t, sy, 6, ink)
    for text, cx in ((f'{a}', box.x), (f'{b}', box.x + box.w)):
        w, h = vb.text.block_size([text], label_font)
        vb.text.draw(cv, [text], label_font, cx - w / 2, sy + 9, muted)
    return box


SERIES = (
    ('A', demo.ACCENT, [(18, 22, 0.35), (30, 40, 0.5), (48, 52, 0.7), (62, 70, 0.85), (70, 86, 1.0)]),
    ('B', demo.ACCENT, [(40, 15, 0.45), (36, 30, 0.45), (52, 34, 0.55), (74, 44, 0.6), (86, 62, 0.7)]),
    ('C', demo.TEAL, [(70, 80, 0.8), (60, 66, 0.7), (44, 62, 0.55), (30, 48, 0.45), (16, 40, 0.4)]),
    ('D', demo.TEAL, [(82, 30, 0.6), (76, 50, 0.75), (84, 66, 0.9), (68, 78, 0.95), (50, 84, 0.85)]),
    ('E', demo.ACCENT, [(26, 70, 0.3), (22, 56, 0.3), (34, 46, 0.4), (40, 28, 0.5), (56, 18, 0.55)]),
)


def draw(n, cv):
    h = 340
    box = vb.Box(demo.W / 2 - h * 0.8, (demo.H - h) / 2 - 10, h * 1.6, h)
    cv.mark('chart', *draw_scatter_playback(cv, box, SERIES, demo.phase(n, 0.2, 2.8), periods=(2010, 2024)))


CAPABILITY = Capability(
    id='scatter-time-playback',
    name='Scatter time playback',
    family='broadcast',
    group='Charts',
    aliases=('animated scatter over time', 'gapminder motion', 'bubble chart playback'),
    definition='Bubbles on a scatter chart drift to new spots and grow or shrink as the years tick by, '
               'each leaving a fading tail of the path it took.',
    phrasings=('play the bubble chart forward through the years so the dots move',
               'animate the scatter plot over time with trails behind each point',
               'show how each country moved on the chart from 2010 to 2024'),
    related=('frame-delay-echo', 'time-remapping', 'hyperlapse', 'accumulation-motion-blur', 'delay',
             'slow-motion'),
    api=('videobuilder.capabilities.broadcast.scatter_time_playback.draw_scatter_playback',
         'videobuilder.capabilities.broadcast.scatter_time_playback.sample'),
    demo=lambda: demo.film(draw),
)
