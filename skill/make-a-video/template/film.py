"""TITLE: one line on what this film is.

    python film.py preview                 # http://127.0.0.1:8000/
    python film.py sheet --format all      # contact sheets
    python film.py render --format all     # film-9x16.mp4, film-16x9.mp4

A starter film from the make-a-video skill. Every colour, font, size and
safe-area number below is a PLACEHOLDER: replace them with the film's own.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# If videobuilder isn't installed, point at a checkout (or set PYTHONPATH):
# sys.path.insert(0, '/path/to/videobuilder')

import videobuilder as vb  # noqa: E402
from videobuilder import Box, fr, per_format, text  # noqa: E402

# ---- assets: vendored fonts (with their licences) live in assets/ ----
for _f in sorted((HERE / 'assets').rglob('*.[ot]tf')):
    text.register(_f)
FAMILY = 'Sans'  # PLACEHOLDER: the vendored font's family name (scripts/fontinfo.py prints it)

# ---- time: pick BPM and fps first; everything below is in beats ----
# 120 bpm at 30 fps is 15 frames a beat; 40 beats is 20 s.
GRID = vb.Grid(fps=30, bpm=120, head_trim=0)  # head_trim: frames cut from the track's head
FPB = GRID.frames_per_beat


# ---- the storyboard: one card per segment, its copy beside it ----
def card(name, beats, copy='', overlap=0, **data):
    """A storyboard line: `beats` long, showing `copy` (a string or list of strings).
    `copy_at` in data is the beat offset when all copy is legible. `overlap`: beats the
    previous segment keeps drawing under this one (a transition, not a cut)."""
    return dict(name=name, beats=beats, copy=copy, overlap=overlap, data=data, children=())


def group(name, *cards):
    """Cards that share one scene (and one entrance) back to back."""
    return dict(name=name, beats=sum(c['beats'] for c in cards), copy='', overlap=0, data={}, children=cards)


def segments(at, items):
    out = []
    for c in items:
        out.append(vb.Segment(c['name'], at, at + c['beats'], dict(copy=c['copy'], **c['data']),
                              children=segments(at, c['children']), overlap=c['overlap']))
        at += c['beats']
    return out


STORYBOARD = [
    card('hook', 8, 'The headline, in a few words'),
    group('points',
          card('point 1', 4, 'First point'),
          card('point 2', 4, 'Second point'),
          card('point 3', 4, 'Third point')),
    card('proof', 10, 'One line on the picture, chart or capture'),
    card('end', 10, 'Call to action', overlap=1),
]
END = sum(c['beats'] for c in STORYBOARD)
TIMELINE = vb.Timeline(GRID, segments(0, STORYBOARD), end=END)

# ---- look: PLACEHOLDERS, replace with the film's own ----
BG = '#000000'
INK = '#ffffff'
MUTED = '#999999'
ACCENT = '#888888'
PANEL = '#222222'


def font(size, weight=400, family=None, **kw):
    """A Font in FAMILY, or another vendored `family` (a mono for code, say)."""
    return vb.Font(family or FAMILY, size, weight=weight, **kw)


# ---- layout: one full table per format, each from its own geometry ----
# Safe areas are PLACEHOLDERS: use the margins the target platform documents.
def layout_9x16():
    frame = Box(0, 0, 1080, 1920)
    safe = frame.pad(220, 70, 380, 70)
    return dict(safe=safe, title=104, body=56, small=40, gap=48,
                panel=safe.pad(safe.h * 0.08, 0).contain(4, 3))


def layout_16x9():
    frame = Box(0, 0, 1920, 1080)
    safe = frame.pad(80, 120)
    text_col, pic_col = safe.row(fr, 1.2 * fr, gap=80)
    return dict(safe=safe, title=120, body=60, small=40, gap=40,
                panel=pic_col.contain(4, 3), side=text_col)


LAYOUTS = {'9x16': layout_9x16(), '16x9': layout_16x9()}

EASE_OUT = vb.bezier(0.16, 1, 0.3, 1)
SETTLE = vb.critical(140)
BOUNCY = dict(stiffness=170, damping=14)


# ---- helpers ----
ENTER = 3  # frames an entrance is already under way on its segment's first frame


def appear(f, delay=0, spring=SETTLE):
    """0 -> 1 entrance, `delay` frames into the shot. With delay 0 it's ENTER
    frames in on the cut frame, so something is on screen as the beat lands."""
    return vb.spring_at(f + ENTER - delay, GRID.fps, **spring)


def fade_out(shot, frames=8):
    """1 -> 0 over a shot's last `frames`. (A shot the next one overlaps needs no fade.)"""
    return vb.interpolate(shot.f, [shot.length - frames, shot.length], [1, 0])


def copy_block(cv, shot, words, fnt, box, colour, align='center', delay=0, valign='center', name='copy'):
    """Wrapped, balanced copy in `box` (`valign` top, center or bottom),
    springing up; marked for checks. Returns the Box drawn."""
    words = '\n'.join(words) if isinstance(words, list) else words
    lines = text.wrap(words, fnt, box.w, balance=True)
    w, h = text.block_size(lines, fnt)
    at = box.anchor(box.w, h, {'top': 'top', 'center': 'center', 'bottom': 'bottom'}[valign])
    s = appear(shot.f, delay)
    with cv.layer(opacity=min(1, s), dy=(1 - s) * 40):
        drawn = text.draw(cv, lines, fnt, at.x, at.y, colour, align=align, width=at.w)
        cv.mark(name, *drawn)  # check.py: inside the safe area, overlapping no other mark
    return drawn


# ---- scenes: pure functions of the shot ----
def hook(cv, shot, L):
    with cv.layer(opacity=fade_out(shot)):
        copy_block(cv, shot, shot.data['copy'], font(L['title'], 700, line_height=1.05), L['safe'], INK)


def points(cv, shot, L):
    # One entrance for the whole group (group_f); each child swaps its line on the cut.
    safe = L['safe']
    p = EASE_OUT(vb.clamp01(shot.group_f / 12))
    cv.rect(safe.x, safe.cy - 4, safe.w * p, 8, ACCENT)
    above = Box(safe.x, safe.y, safe.w, safe.h / 2 - L['gap'])
    copy_block(cv, shot, shot.data['copy'], font(L['body'], 600), above, INK, valign='bottom')


def proof(cv, shot, L):
    panel = L['panel']
    s = appear(shot.f)
    with cv.layer(opacity=min(1, s)):  # no fade: the end card slides over it
        cv.rect(*panel, PANEL, radius=24)  # PLACEHOLDER: an image, a capture (cv.view) or a chart
        cv.mark('panel', *panel)
        under = Box(L['safe'].x, panel.bottom + L['gap'], L['safe'].w, L['safe'].bottom - panel.bottom - L['gap'])
        if 'side' in L:
            under = L['side']
        copy_block(cv, shot, shot.data['copy'], font(L['small']), under, MUTED, delay=6)


def end(cv, shot, L):
    safe = L['safe']
    s = appear(shot.f, 0, BOUNCY)
    with cv.layer(dy=(1 - min(1, s)) * safe.h):  # slides up over the proof during the overlap
        cv.rect(0, 0, cv.width, cv.height, BG)
        copy_block(cv, shot, shot.data['copy'], font(L['title'], 700), safe, INK, delay=4)


SCENES = {'hook': hook, 'points': points, 'proof': proof, 'end': end}


def draw(n, cv):
    L = per_format(LAYOUTS, cv)
    for shot in TIMELINE.live(n):  # back to front: in an overlap, the outgoing shot first
        SCENES[shot.group.name if shot.group else shot.name](cv, shot, L)


FILM = vb.Film(
    draw=draw,
    timeline=TIMELINE,
    formats=('9x16', '16x9'),
    background=BG,
    # audio=vb.Audio(str(HERE / 'assets' / 'music.wav'), fade_out_frames=round(2 * FPB)),
)

if __name__ == '__main__':
    vb.main(__file__)
