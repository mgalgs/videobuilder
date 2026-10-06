"""A timeline overlay for previews and stills: segment bands with names, beat
ticks, a playhead, and the frame / time / beat readout. A tool, not film style:
it never appears in a render.
"""
from .text import Font, draw as draw_text, measure


def readout(film, n):
    """'f 123  4.10s  beat 8.20  intro' for frame `n`."""
    parts = [f'f {n}', f'{n / film.fps:.2f}s']
    tl = film.timeline
    if tl is not None:
        parts.append(f'beat {n / tl.grid.frames_per_beat:.2f}')
        try:
            parts.append(tl.label(n))
        except IndexError:
            pass
    return '  '.join(parts)


def draw(cv, film, n):
    W, H = cv.width, cv.height
    u = min(W, H) / 1080  # 1 at 1080p, so the overlay keeps its size across formats
    font = Font('Sans', 26 * u, weight=600)
    small = Font('Sans', 20 * u, weight=500)
    pad = 24 * u
    bar_h = 30 * u
    x0, x1 = pad, W - pad
    y = H - pad - bar_h
    span = x1 - x0
    total = max(1, film.frames)

    def fx(frame):
        return x0 + span * frame / total

    ctx = cv.ctx
    ctx.save()
    cv.rect(0, y - 60 * u, W, H - y + 60 * u, (0, 0, 0, 0.55))
    tl = film.timeline
    if tl is not None:
        b = tl.grid.b
        shades = ((255, 255, 255, 0.16), (255, 255, 255, 0.08))
        for i, s in enumerate(tl.leaves()):
            a, z = fx(b(s.at)), fx(b(s.until))
            cv.rect(a, y, z - a, bar_h, shades[i % 2])
            name = s.name
            if measure(name, small) < z - a - 8 * u:
                draw_text(cv, name, small, a + 6 * u, y + (bar_h - 20 * u * 1.3) / 2, (255, 255, 255, 0.85))
        for s, parents in tl.walk():
            a, z = fx(b(s.at)), fx(b(s.until))
            if s.children:  # a group: a bracket over its children, named
                gy = y - (16 + 6 * len(parents)) * u
                cv.rect(a, gy, z - a, 2 * u, (255, 255, 255, 0.6))
                draw_text(cv, s.name, small, a, gy - 26 * u, (255, 255, 255, 0.75))
            if s.overlap:  # the previous segment still drawing under this one
                cv.rect(a, y + bar_h - 6 * u, fx(b(s.at + s.overlap)) - a, 6 * u, (255, 210, 80, 0.8))
        beats = int(tl.end) + 1
        every = max(1, round(beats / (span / (6 * u))))  # keep ticks >= ~6 px apart
        for k in range(0, beats, every):
            x = fx(b(k))
            tall = k % 4 == 0
            cv.rect(x - u / 2, y - (10 if tall else 5) * u, u, (10 if tall else 5) * u, (255, 255, 255, 0.8 if tall else 0.45))
        for c in tl.cut_frames():
            cv.rect(fx(c) - u, y, 2 * u, bar_h, (255, 255, 255, 0.6))
    else:
        cv.rect(x0, y, span, bar_h, (255, 255, 255, 0.1))
    px = fx(n)
    cv.rect(px - 1.5 * u, y - 4 * u, 3 * u, bar_h + 8 * u, '#ff3b30')
    draw_text(cv, readout(film, n), font, x0, y - 48 * u, '#ffffff')
    ctx.restore()
