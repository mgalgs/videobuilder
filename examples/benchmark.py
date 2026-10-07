"""A 20-second benchmark reel: a bar chart drawn with the canvas, in 9:16 and 16:9.

    python -m videobuilder preview examples/benchmark.py
    python -m videobuilder render examples/benchmark.py --format all

Made by an agent following the make-a-video skill (skill/make-a-video/) on
its second cold trial, from a one-paragraph brief. Lumen and its numbers
are invented. It shows a storyboard in a timeline (groups, an overlap), a
chart whose bars grow on the beat and whose numbers count up, a chart laid
out differently per format (horizontal bars in 9:16, columns in 16:9), two
vendored variable fonts, and marks that the skill's check.py reads. The
look is this film's own, not the framework's. The music is a placeholder
bed generated at import by the skill's make_track.py.

STORYBOARD (120 bpm, 30 fps, 15 frames a beat; 40 beats = 20 s)

| segment        | beats | on screen                                  | copy                                                        | motion |
|----------------|-------|--------------------------------------------|-------------------------------------------------------------|--------|
| hook           | 0-8   | headline over drifting JSON text           | "1 GB of JSON. How fast?"                                   | line 1 springs up, "How fast?" lands on beat 2; fades out |
| chart / bars   | 8-20  | title, chart; bars grow on beats 10,11,12, Lumen on 14 | "Time to parse 1 GB of JSON. Same machine, lower is better." | title in on the cut; each bar springs out on its beat, its number counting up |
| chart / verdict| 20-28 | others dim, Lumen glows, callout           | "2.4x faster than the next best"                            | hard cut: note swaps to the callout |
| end            | 28-40 | wordmark, tagline, URL pill                | "Lumen. The open-source JSON parser. github.com/lumen-json/lumen" | slides up over the chart (overlap 1) |

Per format: 9:16 stacks title / horizontal bars / callout; 16:9 puts the
copy in a left column and the bars as vertical columns on the right.
"""
import hashlib
import os
import sys
import tempfile
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent

import videobuilder as vb  # noqa: E402
from videobuilder import Box, fr, per_format, text  # noqa: E402

# ---- assets: vendored fonts (with their licences) live in assets/ ----
for _f in sorted((HERE / 'assets').glob('*.[ot]tf')):
    text.register(_f)
FAMILY = 'Inter'
MONO = 'SourceCodeVF'

# ---- time ----
GRID = vb.Grid(fps=30, bpm=120, head_trim=0)
FPB = GRID.frames_per_beat


# ---- the storyboard ----
def card(name, beats, copy='', overlap=0, **data):
    return dict(name=name, beats=beats, copy=copy, overlap=overlap, data=data, children=())


def group(name, *cards):
    return dict(name=name, beats=sum(c['beats'] for c in cards), copy='', overlap=0, data={}, children=cards)


def segments(at, items):
    out = []
    for c in items:
        out.append(vb.Segment(c['name'], at, at + c['beats'], dict(copy=c['copy'], **c['data']),
                              children=segments(at, c['children']), overlap=c['overlap']))
        at += c['beats']
    return out


STORYBOARD = [
    card('hook', 8, '1 GB of JSON. How fast?'),
    group('chart',
          card('bars', 12, 'Time to parse 1 GB of JSON. Same machine, lower is better.'),
          card('verdict', 8, '2.4× faster than the next best')),
    card('end', 12, 'Lumen. The open-source JSON parser. github.com/lumen-json/lumen', overlap=1),
]
END = sum(c['beats'] for c in STORYBOARD)
TIMELINE = vb.Timeline(GRID, segments(0, STORYBOARD), end=END)

# The data, in display order (fastest first). `beat`: when the bar starts
# growing, in beats from the chart group's start. Slowest grows first; Lumen last.
BARS = [
    dict(name='Lumen', secs=1.9, beat=6, hero=True),
    dict(name='Parser A', secs=4.6, beat=4),
    dict(name='Parser B', secs=7.2, beat=3),
    dict(name='Parser C', secs=11.8, beat=2),
]
AXIS_MAX = 12.0
TICKS = (0, 4, 8, 12)
URL = 'github.com/lumen-json/lumen'  # PLACEHOLDER: Lumen is invented

# ---- look (chosen for this film) ----
BG = '#0d1117'
INK = '#f3f5f8'
MUTED = '#8b95a5'
FAINT = '#2a313c'
BAR = '#4a5363'
ACCENT = '#ffb547'   # "lumen": a warm light
ACCENT_INK = '#1a1306'


def font(size, weight=400, family=None, **kw):
    return vb.Font(family or FAMILY, size, weight=weight, **kw)


# ---- layout: one table per format ----
# Safe areas: 9:16 keeps clear of the top bar and the caption/button stack
# that Reels/TikTok/Shorts draw over the bottom and right; 16:9 is title-safe.
def layout_9x16():
    frame = Box(0, 0, 1080, 1920)
    safe = frame.pad(220, 90, 400, 70)
    title, chart, note = safe.column(200, fr, 240, gap=50)
    return dict(safe=safe, orient='h', title=title, chart=chart, note=note,
                hook=128, h1=72, sub=44, verdict=100, label=42, value=46, tick=32,
                word=200, tag=50, url=40, gap=40)


def layout_16x9():
    frame = Box(0, 0, 1920, 1080)
    safe = frame.pad(90, 130)
    left, chart = safe.row(fr, 1.35 * fr, gap=110)
    title, note = left.column(fr, fr, gap=40)
    return dict(safe=safe, orient='v', title=title, chart=chart, note=note,
                hook=150, h1=88, sub=44, verdict=120, label=36, value=46, tick=30,
                word=200, tag=56, url=42, gap=40)


LAYOUTS = {'9x16': layout_9x16(), '16x9': layout_16x9()}

EASE_OUT = vb.bezier(0.16, 1, 0.3, 1)
SETTLE = vb.critical(140)
GROW = dict(stiffness=150, damping=15)    # a bar overshoots a touch, then settles
BOUNCY = dict(stiffness=170, damping=14)
ENTER = 3


def appear(f, delay=0, spring=SETTLE):
    return vb.spring_at(f + ENTER - delay, GRID.fps, **spring)


def fade_out(shot, frames=8):
    return vb.interpolate(shot.f, [shot.length - frames, shot.length], [1, 0])


def copy_block(cv, f, words, fnt, box, colour, name, align='center', delay=0, valign='center', rise=40):
    lines = text.wrap(words, fnt, box.w, balance=True)
    w, h = text.block_size(lines, fnt)
    at = box.anchor(box.w, h, valign)
    s = appear(f, delay)
    with cv.layer(opacity=vb.clamp01(s), dy=(1 - s) * rise):
        drawn = text.draw(cv, lines, fnt, at.x, at.y, colour, align=align, width=at.w)
        cv.mark(name, *drawn)
    return drawn


# ---- generated backdrop: drifting JSON, seeded, a pure function of n ----
def _json_lines():
    import random
    rnd = random.Random(7)
    keys = ['id', 'name', 'tags', 'ts', 'score', 'ok', 'user', 'geo', 'items', 'v']
    out = []
    for _ in range(60):
        parts = []
        for _ in range(rnd.randint(3, 6)):
            k = rnd.choice(keys)
            v = rnd.choice([str(rnd.randint(0, 99999)), '"%s"' % rnd.choice(['a1f', 'ok', 'lumen', 'x9', 'utf8']),
                            'true', 'null', '[%d, %d]' % (rnd.randint(0, 99), rnd.randint(0, 99))])
            parts.append('"%s": %s' % (k, v))
        out.append('{' + ', '.join(parts) + '},')
    return out


JSON_LINES = _json_lines()


def json_backdrop(cv, n, alpha):
    fnt = font(30, 400, MONO)
    lh = text.line_height(fnt) * 1.25
    drift = n * 1.6  # px per frame, upward
    rows = int(cv.height / lh) + 2
    first = int(drift // lh)
    for r in range(rows):
        i = first + r
        y = i * lh - drift
        x = -((i * 137) % 400)
        text.draw(cv, JSON_LINES[i % len(JSON_LINES)] * 2, fnt, x, y, INK, alpha=0.06 * alpha)


# ---- scenes ----
def hook(cv, shot, L):
    safe = L['safe']
    out = fade_out(shot)
    json_backdrop(cv, shot.f, out)
    with cv.layer(opacity=out):
        f1 = font(L['hook'], 800, line_height=1.0, tracking=-0.02)
        l1 = text.wrap('1 GB of JSON.', f1, safe.w)
        l2 = text.wrap('How fast?', f1, safe.w)
        h = text.block_size(l1, f1)[1] + text.block_size(l2, f1)[1] + L['gap'] * 0.5
        top = safe.cy - h / 2
        a = appear(shot.f)
        with cv.layer(opacity=vb.clamp01(a), dy=(1 - a) * 50):
            b1 = text.draw(cv, l1, f1, safe.x, top, INK, align='center', width=safe.w)
            cv.mark('headline', *b1)
        b = appear(shot.f, delay=GRID.b(2) - ENTER, spring=BOUNCY)  # lands on beat 2
        with cv.layer(opacity=vb.clamp01(b), dy=(1 - b) * 50):
            b2 = text.draw(cv, l2, f1, safe.x, b1.bottom + L['gap'] * 0.5, ACCENT, align='center', width=safe.w)
            cv.mark('question', *b2)


def bar_grow(shot, bar):
    """0 -> 1 (with a little overshoot): the bar is already moving on its beat."""
    return max(0.0, vb.spring_at(shot.group_f - GRID.b(bar['beat']) + ENTER, GRID.fps, **GROW))


def chart(cv, shot, L):
    g = shot.group_f
    verdict = shot.name == 'verdict'
    vf = shot.f if verdict else -1
    dim = vb.interpolate(vf, [0, 10], [1, 0.35], ease=EASE_OUT) if verdict else 1.0

    # title and note (the note swaps to the callout on the verdict cut)
    copy_block(cv, g, 'Time to parse 1 GB of JSON', font(L['h1'], 750, line_height=1.08, tracking=-0.01),
               L['title'], INK, 'title', align='left' if L['orient'] == 'v' else 'center',
               valign='bottom' if L['orient'] == 'v' else 'center')
    if not verdict:
        copy_block(cv, g, 'Same machine.\nLower is better.', font(L['sub'], 450, line_height=1.3), L['note'], MUTED,
                   'note', align='left' if L['orient'] == 'v' else 'center',
                   valign='top' if L['orient'] == 'v' else 'center', delay=6)
    else:
        verdict_block(cv, shot, L)

    if L['orient'] == 'h':
        bars_horizontal(cv, shot, L, dim)
    else:
        bars_vertical(cv, shot, L, dim)
    cv.mark('chart', *L['chart'])


def verdict_block(cv, shot, L):
    box = L['note']
    v = 'v' == L['orient']
    big = font(L['verdict'], 850, line_height=1.0, tracking=-0.02)
    small = font(L['sub'], 500, line_height=1.25)
    s = appear(shot.f, spring=BOUNCY)
    l1 = ['2.4× faster']
    l2 = text.wrap('than the next best', small, box.w)
    h1, h2 = text.block_size(l1, big)[1], text.block_size(l2, small)[1]
    total = h1 + 14 + h2
    y = box.y if v else box.y + (box.h - total) / 2
    align = 'left' if v else 'center'
    with cv.layer(opacity=vb.clamp01(s), dy=(1 - s) * 40):
        b1 = text.draw(cv, l1, big, box.x, y, ACCENT, align=align, width=box.w)
        b2 = text.draw(cv, l2, small, box.x, b1.bottom + 14, INK, align=align, width=box.w)
        cv.mark('verdict', b1.x if v else min(b1.x, b2.x), b1.y, max(b1.w, b2.w), b2.bottom - b1.y)


def value_label(bar, p):
    return f'{bar["secs"] * min(1.0, p):.1f} s'


def glow(cv, x, y, w, h, radius, k):
    for i, (spread, a) in enumerate(((22, 0.10), (12, 0.16), (5, 0.25))):
        cv.rect(x - spread, y - spread, w + 2 * spread, h + 2 * spread, ACCENT, radius=radius + spread, alpha=a * k)


def bars_horizontal(cv, shot, L, dim):
    """9:16: one row per library, bars grow to the right, the number rides the bar's end."""
    box = L['chart']
    lab_f = font(L['label'], 600)
    val_f = font(L['value'], 700)
    tick_f = font(L['tick'], 450)
    val_w = text.measure('11.8 s', val_f) + 24
    axis_h = text.line_height(tick_f) + 16
    plot = Box(box.x, box.y, box.w - val_w, box.h - axis_h)
    rows = plot.column(*([fr] * len(BARS)), gap=36)
    lh = text.line_height(lab_f)
    k = (plot.w) / AXIS_MAX
    g_in = EASE_OUT(vb.clamp01((shot.group_f + ENTER) / 12))
    # gridlines + axis
    for t in TICKS:
        x = plot.x + t * k
        cv.line(x, plot.y, x, plot.y + (plot.bottom - plot.y) * g_in, FAINT, width=2)
        text.draw(cv, f'{t} s', tick_f, x - 60, plot.bottom + 12, MUTED, align='center', width=120, alpha=g_in)
    verdict_k = vb.clamp01(shot.f / 10) if shot.name == 'verdict' else 0
    for bar, row in zip(BARS, rows):
        p = bar_grow(shot, bar)
        hero = bar.get('hero')
        alpha = 1 if hero else dim
        bh = min(110, row.h - lh - 12)
        by = row.y + lh + 12
        label_in = vb.clamp01((shot.group_f - GRID.b(bar['beat']) + ENTER) / 5)
        text.draw(cv, [bar['name']], lab_f, row.x, row.y, ACCENT if hero else INK, alpha=alpha * max(label_in, 0.0))
        if p <= 0:
            continue
        w = max(0.0, bar['secs'] * k * p)
        if hero and verdict_k > 0:
            glow(cv, row.x, by, w, bh, 10, verdict_k)
        cv.rect(row.x, by, w, bh, ACCENT if hero else BAR, radius=10, alpha=alpha)
        text.draw(cv, [value_label(bar, p)], val_f, row.x + w + 18, by + (bh - text.line_height(val_f)) / 2,
                  ACCENT if hero else INK, alpha=alpha * vb.clamp01(p * 3))


def bars_vertical(cv, shot, L, dim):
    """16:9: columns side by side, growing up; name under, number on top."""
    box = L['chart']
    lab_f = font(L['label'], 600)
    val_f = font(L['value'], 700)
    tick_f = font(L['tick'], 450)
    lab_h = text.line_height(lab_f) + 20
    val_h = text.line_height(val_f) + 16
    tick_w = text.measure('12 s', tick_f) + 20
    plot = Box(box.x + tick_w, box.y + val_h, box.w - tick_w, box.h - val_h - lab_h)
    cols = plot.row(*([fr] * len(BARS)), gap=48)
    k = plot.h / AXIS_MAX
    g_in = EASE_OUT(vb.clamp01((shot.group_f + ENTER) / 12))
    for t in TICKS:
        y = plot.bottom - t * k
        cv.line(plot.x, y, plot.x + plot.w * g_in, y, FAINT, width=2)
        text.draw(cv, f'{t} s', tick_f, box.x, y - text.line_height(tick_f) / 2, MUTED, align='right',
                  width=tick_w - 16, alpha=g_in)
    verdict_k = vb.clamp01(shot.f / 10) if shot.name == 'verdict' else 0
    for bar, col in zip(BARS, cols):
        p = bar_grow(shot, bar)
        hero = bar.get('hero')
        alpha = 1 if hero else dim
        label_in = vb.clamp01((shot.group_f - GRID.b(bar['beat']) + ENTER) / 5)
        text.draw(cv, [bar['name']], lab_f, col.x - 20, plot.bottom + 20, ACCENT if hero else INK,
                  align='center', width=col.w + 40, alpha=alpha * label_in)
        if p <= 0:
            continue
        h = max(0.0, bar['secs'] * k * p)
        if hero and verdict_k > 0:
            glow(cv, col.x, plot.bottom - h, col.w, h, 10, verdict_k)
        cv.rect(col.x, plot.bottom - h, col.w, h, ACCENT if hero else BAR, radius=10, alpha=alpha)
        text.draw(cv, [value_label(bar, p)], val_f, col.x - 20, plot.bottom - h - val_h, ACCENT if hero else INK,
                  align='center', width=col.w + 40, alpha=alpha * vb.clamp01(p * 3))


def end(cv, shot, L):
    safe = L['safe']
    s = appear(shot.f, 0, BOUNCY)
    with cv.layer(dy=(1 - min(1, s)) * cv.height):
        cv.rect(0, 0, cv.width, cv.height, BG)
        word_f = font(L['word'], 850, tracking=-0.035, line_height=1.0)
        tag_f = font(L['tag'], 500)
        url_f = font(L['url'], 600, MONO)
        word_w = text.measure('Lumen', word_f)
        dot = L['word'] * 0.22
        tag_lines = text.wrap('The open-source JSON parser', tag_f, safe.w, balance=True)
        pill = text.box(URL, url_f, padding=(22, 36))
        wh = text.line_height(word_f)
        th = text.block_size(tag_lines, tag_f)[1]
        total = wh + 30 + th + 70 + pill.h
        y = safe.y + (safe.h - total) / 2
        # wordmark: a lit dot, then the name
        a = appear(shot.f, 4)
        gx = safe.cx - (word_w + dot * 1.6) / 2
        with cv.layer(opacity=vb.clamp01(a), dy=(1 - a) * 40):
            pulse = 0.5 + 0.5 * vb.clamp01(1 - ((shot.f % FPB) / FPB))  # glows on every beat
            cx, cy = gx + dot / 2, y + wh * 0.30
            for r, al in ((dot * 1.6, 0.10), (dot * 1.1, 0.18)):
                cv.rect(cx - r, cy - r, 2 * r, 2 * r, ACCENT, radius=r, alpha=al * pulse)
            cv.rect(cx - dot / 2, cy - dot / 2, dot, dot, ACCENT, radius=dot / 2)
            wb = text.draw(cv, ['Lumen'], word_f, gx + dot * 1.6, y, INK)
            cv.mark('wordmark', gx, wb.y, wb.right - gx, wb.h)
        copy_block(cv, shot.f, 'The open-source JSON parser', tag_f,
                   Box(safe.x, y + wh + 30, safe.w, th), MUTED, 'tagline', delay=8, valign='top')
        b = appear(shot.f, 14, BOUNCY)
        pb = Box(safe.cx - pill.w / 2, y + wh + 30 + th + 70, pill.w, pill.h)
        with cv.layer(opacity=vb.clamp01(b), dy=(1 - b) * 40):
            cv.rect(*pb, ACCENT, radius=pb.h / 2)
            text.draw_in(cv, pb, URL, url_f, ACCENT_INK, padding=(22, 36), align='center')
            cv.mark('url', *pb)


SCENES = {'hook': hook, 'chart': chart, 'end': end}


def draw(n, cv):
    L = per_format(LAYOUTS, cv)
    for shot in TIMELINE.live(n):
        SCENES[shot.group.name if shot.group else shot.name](cv, shot, L)


# FILM.keyframes replaces the sheet's default in/middle/out frames, so list
# those too, plus the frames where the bars have all settled.
def _keyframes():
    keys = {}
    for seg in TIMELINE.leaves():
        a, b = TIMELINE.span(seg.name)
        for n, tag in ((a, 'in'), ((a + b) // 2, 'mid'), (b - 1, 'out')):
            keys[n] = f'{seg.name} {tag}'
    keys[GRID.b(17.5)] = 'bars settled'
    return tuple(sorted(keys.items()))


KEYFRAMES = _keyframes()


def _music():
    """The placeholder bed, made once by the skill's make_track.py and cached."""
    args = dict(bpm=GRID.bpm, beats=int(END), loop='major', tail=1.0)
    key = hashlib.sha1(repr(sorted(args.items())).encode()).hexdigest()[:12]
    path = os.path.join(tempfile.gettempdir(), f'videobuilder-benchmark-{key}.wav')
    if not os.path.exists(path):
        sys.path.insert(0, str(HERE.parent / 'skill' / 'make-a-video' / 'scripts'))
        from make_track import synth
        data = synth(args['bpm'], args['beats'], loop=args['loop'], tail=args['tail'])
        tmp = f'{path}.{os.getpid()}.tmp'
        with wave.open(tmp, 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(48000)
            w.writeframes(data.tobytes())
        os.replace(tmp, path)
    return path


FILM = vb.Film(
    draw=draw,
    timeline=TIMELINE,
    formats=('9x16', '16x9'),
    background=BG,
    audio=vb.Audio(_music(), gain_db=-3, fade_out_frames=round(2 * FPB)),
    keyframes=KEYFRAMES,
)

if __name__ == '__main__':
    vb.main(__file__)
