"""Title: terminal. A title typed into a phosphor-green-black editor: big
monospace characters land one at a time with a human, uneven cadence, a
block cursor rides the end of the line, and an optional answer line types
in after a beat's pause, in the accent's quieter sibling. Once it's all
typed the cursor blinks on the beat.

The editor is the whole frame, not a window in it: a line-number gutter
runs top to bottom, empty rows past the end show a `~` the way a modal
editor does, and faint scanlines and a slow rolling band sit over it all,
so a tall 9:16 frame is full screen, not a box with bands. Every row sits
on one grid: a title line takes two rows, an answer line one.
"""
import math
import random

import cairo

import videobuilder as vb
from videobuilder import text

from .. import kit
from ..schema import Component, Slot
from ._title_util import frames_per_beat

SCREEN = '#0d1113'
PAD = 36
GUTTER = 56
TITLE_SIZES = tuple(range(110, 21, -2))


def _mono(size, weight, rows_px=None):
    lh = None if rows_px is None else rows_px / size
    return kit.mono(size, weight, line_height=lh)


STATUS_H = 30
STATUS_F = kit.mono(14, 600, tracking=0.06)


def _layout(cv, title, answer):
    """Fonts, wrapped lines and the row grid for this format and copy: the
    editor's rows take the safe area above the status bar."""
    s = vb.Box.of(cv).pad(PAD)
    s = vb.Box(s.x, s.y, s.w, s.h - STATUS_H - 10)
    text_w = s.w - GUTTER - 4
    tall = cv.height > cv.width * 1.2
    max_rows_h = s.h * (0.62 if tall else 0.86)
    for size in TITLE_SIZES:
        row = round(size * 0.68)          # one grid row; a title line is two
        tf = _mono(size, 700, row * 2)
        prompt_w = text.measure('> ', tf)
        tl = text.wrap(title, tf, text_w - prompt_w)
        af = _mono(max(15, min(34, row * 0.66)), 500, row)
        al = text.wrap('→ ' + answer, af, text_w) if answer else ()
        fits = all(text.measure(ln, tf) <= text_w - prompt_w for ln in tl) and \
            all(text.measure(ln, af) <= text_w for ln in al)
        if fits and row * (2 * len(tl) + (1 + len(al) if al else 0)) <= max_rows_h:
            break
    return s, row, tf, tl, af, al, prompt_w


def _schedule(chars, seed, per_char):
    """Seeded keystroke times (frames from the start of the line): a little
    uneven, a longer reach after a space or a comma."""
    rnd = random.Random(seed)
    t, out = 0.0, []
    for ch in chars:
        out.append(t)
        t += per_char * rnd.uniform(0.55, 1.45) * (1.8 if ch in ' ,.' else 1.0)
    return out, t


def _typed(times, local):
    return sum(1 for t in times if t <= local)


def draw(cv, shot):
    data = shot.data
    accent = data['accent']
    soft = kit.mix(accent, kit.INK, 0.55)
    fpb = frames_per_beat(shot)
    n = shot.f
    cv.fill(SCREEN)

    title, answer = data['title'], data['answer']
    s, row, tf, tl, af, al, prompt_w = _layout(cv, title, answer)
    joined_title = ''.join(tl)
    t_times, t_len = _schedule(joined_title, f't:{title}', 1.25)
    a_text = ''.join(al)
    a_times, a_len = _schedule(a_text, f'a:{answer}', 0.75) if al else ([], 0)

    # Squeeze the typing to fit a short shot: everything typed by 65% of it.
    t0 = fpb * 0.25
    gap = fpb * 0.5
    natural = t0 + t_len + (gap + a_len if al else 0)
    k = min(1.0, shot.length * 0.65 / natural) if natural else 1.0
    t_times = [t * k for t in t_times]
    a_times = [t * k for t in a_times]
    t_end = t0 + t_len * k
    a0 = math.ceil((t_end + gap * k) / (fpb / 2)) * (fpb / 2)  # the answer starts on a half beat
    a_end = a0 + a_len * k

    # ---- the grid: content rows centred, gutter numbers / tildes everywhere ----
    content_rows = 2 * len(tl) + (1 + len(al) if al else 0)
    total_rows = int(s.h // row)
    first = max(0, round((total_rows - content_rows) / 2 + 0.01))
    gf = kit.mono(max(12, min(17, row * 0.5)), 500)
    gl = text.line_height(gf)
    title_rows = {first + 2 * i: i for i in range(len(tl))}
    answer_rows = {first + 2 * len(tl) + 1 + i: i for i in range(len(al))}
    typed_t = _typed(t_times, n - t0)
    typed_a = _typed(a_times, n - a0) if al else 0
    # which logical line the cursor is on
    if typed_a > 0 or (al and n >= a0):
        cur_row = first + 2 * len(tl) + 1 + _line_of(al, typed_a)
    else:
        cur_row = first + 2 * _line_of(tl, typed_t)
    line_no = 0
    for r in range(total_rows):
        y = s.y + r * row
        in_content = first <= r < first + content_rows
        if r < first or r in title_rows or r in answer_rows or (in_content and r == first + 2 * len(tl)):
            line_no += 1
            label, color = f'{line_no:>2}', kit.MUTED if r == cur_row else '#555c66'
        elif in_content:
            continue  # the second row of a title line: a wrapped row has no number
        else:
            label, color = ' ~', '#3b424b'
        if r == cur_row:
            cv.rect(s.x - 8, y, s.w + 16, row * (2 if r in title_rows else 1), '#161c1f')
        text.draw(cv, [label], gf, s.x, y + (row - gl) / 2, color)

    tx = s.x + GUTTER
    # A soft phosphor bloom behind the copy.
    cy = s.y + (first + content_rows / 2) * row
    g = cairo.RadialGradient(tx + (s.w - GUTTER) / 2, cy, 10, tx + (s.w - GUTTER) / 2, cy, s.w * 0.75)
    g.add_color_stop_rgba(0, *vb.rgba(accent, 0.10))
    g.add_color_stop_rgba(1, *vb.rgba(accent, 0.0))
    cv.ctx.set_source(g)
    cv.ctx.paint()

    # ---- the title, typed ----
    cursor = None
    left = typed_t
    for i, line in enumerate(tl):
        y = s.y + (first + 2 * i) * row
        if i == 0 and n >= t0 - 2:
            text.draw(cv, ['>'], tf, tx, y, accent)
        shown = line[:max(0, left)]
        left -= len(line)
        if shown:
            box = text.draw(cv, [shown], tf, tx + prompt_w, y, kit.INK)
            cv.mark(f'title-{i}', box.x, box.y, box.w, box.h)
        if (left < 0 or (i == len(tl) - 1 and not al)) and cursor is None:
            cursor = (tx + prompt_w + text.measure(shown, tf), y, tf)
    if typed_t == len(joined_title) and cursor is None and al and n < a0:
        last = tl[-1]
        cursor = (tx + prompt_w + text.measure(last, tf), s.y + (first + 2 * len(tl) - 2) * row, tf)

    # ---- the answer, typed after a beat's pause ----
    if al and n >= a0:
        cursor = None
        left = typed_a
        for i, line in enumerate(al):
            y = s.y + (first + 2 * len(tl) + 1 + i) * row
            shown = line[:max(0, left)]
            left -= len(line)
            if shown:
                box = text.draw(cv, [shown], af, tx, y, soft)
                cv.mark(f'answer-{i}', box.x, box.y, box.w, box.h)
            if (left < 0 or i == len(al) - 1) and cursor is None:
                cursor = (tx + text.measure(shown, af), y, af)

    # ---- the cursor: solid while typing, blinking on the beat once done ----
    if cursor is not None:
        typing = n < (a_end if al else t_end) + 2
        on = typing or ((n % fpb) < fpb * 0.5)
        if on and n >= t0 - 2:
            cx, cyy, cf = cursor
            lh = text.line_height(cf)
            cw = text.measure('M', cf)
            cv.rect(cx + 2, cyy + lh * 0.12, cw * 0.62, lh * 0.76, accent)

    # ---- the status bar: the editor's mode, and where the cursor is ----
    sy = s.bottom + 10
    done = n >= (a_end if al else t_end) + fpb * 0.5
    mode = 'NORMAL' if done else 'INSERT'
    cv.rect(s.x - 8, sy, s.w + 16, STATUS_H, '#182024')
    sl = text.line_height(STATUS_F)
    mw = text.measure(mode, STATUS_F) + 20
    cv.rect(s.x - 8, sy, mw, STATUS_H, accent if not done else kit.MUTED)
    text.draw(cv, [mode], STATUS_F, s.x + 2, sy + (STATUS_H - sl) / 2, SCREEN)
    if cursor is not None:
        line_no_at = (cur_row - first) // 2 + 1 + first if cur_row in title_rows else \
            first + len(tl) + 1 + (cur_row - first - 2 * len(tl))
        col = (typed_a - sum(len(x) for x in al[:_line_of(al, typed_a)]) if al and n >= a0 else
               typed_t - sum(len(x) for x in tl[:_line_of(tl, typed_t)]) + 2) + 1
        pos = f'ln {line_no_at}, col {col}'
        pw = text.measure(pos, STATUS_F)
        text.draw(cv, [pos], STATUS_F, s.right - pw, sy + (STATUS_H - sl) / 2, kit.MUTED)
    cv.mark('status', s.x - 8, sy, s.w + 16, STATUS_H)

    # ---- the glass: still scanlines and a vignette ----
    ctx = cv.ctx
    ctx.set_source_rgba(0, 0, 0, 0.22)
    for y in range(0, cv.height, 4):
        ctx.rectangle(0, y, cv.width, 1.4)
    ctx.fill()
    vg = cairo.RadialGradient(cv.width / 2, cv.height / 2, min(cv.width, cv.height) * 0.4,
                              cv.width / 2, cv.height / 2, max(cv.width, cv.height) * 0.75)
    vg.add_color_stop_rgba(0, 0, 0, 0, 0)
    vg.add_color_stop_rgba(1, 0, 0, 0, 0.55)
    ctx.set_source(vg)
    ctx.paint()


def _line_of(lines, typed):
    """Which of `lines` the `typed`-th character falls on."""
    for i, line in enumerate(lines):
        if typed < len(line) or i == len(lines) - 1:
            return i
        typed -= len(line)
    return 0


COMPONENT = Component(
    id='terminal-title',
    kind='title',
    description=('A title typed into a full-screen terminal in big monospace: uneven keystrokes, a block cursor, '
                 'an optional answer line that types in after a pause, line numbers and scanlines.'),
    tags=('title', 'terminal', 'typewriter', 'mono', 'code', 'developer', 'question'),
    formats=('16x9', '9x16', '1x1'),
    beats=(4, 8),
    slots=(
        Slot('title', 'text', True, 'The line that types on: a question, a command or a short claim.',
             max_length=36),
        Slot('answer', 'text', False, 'A second, smaller line that answers the first.', max_length=48),
        Slot('accent', 'color', False, 'Prompt, cursor and glow colour; the answer line uses a paler tint of it.'),
    ),
    sample={'title': 'what changed overnight?', 'answer': 'Everything you shipped, in one place.',
            'accent': kit.TEAL},
    draw=draw,
)
