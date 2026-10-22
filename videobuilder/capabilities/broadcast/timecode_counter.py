"""Timecode counter: an HH:MM:SS:FF readout that steps forward one frame at a
time as the film plays, the frames field spinning fastest and carrying into
seconds, minutes and hours like an edit suite's clock."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def timecode(frame, fps=30, start=0, drop_frame=False):
    """The SMPTE timecode text `HH:MM:SS:FF` of `frame` (counted from 0) at
    a whole-number `fps`, offset by `start` frames (e.g. `start=fps * 3600`
    for a reel that begins at 01:00:00:00). With `drop_frame` (29.97 shown
    as `fps=30`, or 59.94 as 60) frame numbers 0 and 1 (0-3 at 60) are
    skipped at the start of every minute except each tenth, and the last
    separator is `;`. Hours wrap at 24."""
    n = int(frame) + int(start)
    sep = ':'
    if drop_frame:
        drop = round(fps / 15)                     # 2 at 30, 4 at 60
        per_min = fps * 60 - drop
        per_ten = per_min * 10 + drop
        tens, rem = divmod(n, per_ten)
        n += drop * 9 * tens + (drop * ((rem - drop) // per_min) if rem > drop else 0)
        sep = ';'
    ff = n % fps
    s = n // fps
    return f'{s // 3600 % 24:02d}:{s // 60 % 60:02d}:{s % 60:02d}{sep}{ff:02d}'


def draw_timecode(cv, font, x, y, frame, color, frames_color=None, **kw):
    """Draw the timecode of `frame` from its top-left (x, y) in `font` (use a
    monospaced one so the digits never shift). The frames field is drawn in
    `frames_color` when given, to show it is the one ticking. `kw` goes to
    `timecode`. Returns the Box of the text."""
    text = timecode(frame, **kw)
    head, tail = text[:-2], text[-2:]
    vb.text.draw(cv, [head], font, x, y, color)
    vb.text.draw(cv, [tail], font, x + vb.text.measure(head, font), y, frames_color or color)
    w, h = vb.text.block_size([text], font)
    return vb.Box(x, y, w, h)


START = 30 * (59 * 60 + 58)  # 00:59:58:00, so the demo rolls over into the hour


def draw(n, cv):
    pw, ph = 720, 260
    px, py = (demo.W - pw) / 2, (demo.H - ph) / 2
    cv.shadow(px, py, pw, ph, radius=18, dy=10, blur=28, color=(0, 0, 0, 0.45))
    cv.rect(px, py, pw, ph, '#1b1f27', radius=18)
    cv.rect(px, py, pw, ph, demo.LINE, radius=18, alpha=0.25)
    cv.rect(px + 2, py + 2, pw - 4, ph - 4, '#1b1f27', radius=16)
    vb.text.draw(cv, ['TC  30 FPS'], demo.font(18, 800), px + 32, py + 26, demo.TEAL)
    vb.text.draw(cv, ['● REC'], demo.font(18, 800), px + pw - 92, py + 26,
                 demo.ACCENT, alpha=1.0 if n // 15 % 2 == 0 else 0.25)
    f = demo.mono(96, 600)
    text = timecode(n, start=START)
    w, h = vb.text.block_size([text], f)
    box = draw_timecode(cv, f, (demo.W - w) / 2, py + 70, n, demo.INK, frames_color=demo.ACCENT, start=START)
    cv.mark('timecode', *box)
    ff = (n + START) % 30
    step, tw = 18, 8
    tx = (demo.W - (29 * step + tw)) / 2
    for i in range(30):
        on = i == ff
        cv.rect(tx + i * step, py + ph - 44 - (6 if on else 0), tw, 16 + (6 if on else 0),
                demo.ACCENT if on else demo.MUTED, radius=3, alpha=1.0 if on else 0.35)


TECHNIQUE = Technique(
    id='timecode-counter',
    name='Timecode counter',
    family='broadcast',
    group='Timers & indicators',
    aliases=('running timecode', 'SMPTE counter', 'SMPTE timecode', 'TC readout'),
    definition='An hours, minutes, seconds and frames readout in fixed-width digits that steps forward '
               'one frame at a time, the frame digits racing and rolling over into the seconds.',
    phrasings=('put a ticking edit-suite timecode on screen',
               'show the HH:MM:SS:FF clock counting up frame by frame',
               'add a frame counter like the one in a video editor'),
    related=('camcorder-timecode-overlay', 'timing', 'number-count-down', 'time-remapping',
             'game-clock-countdown', 'number-count-up'),
    api=('videobuilder.techniques.broadcast.timecode_counter.timecode',
         'videobuilder.techniques.broadcast.timecode_counter.draw_timecode'),
    demo=lambda: demo.film(draw),
)
