"""Camcorder timecode overlay: the on-screen display of a home video camera
laid over the picture -- a blinking REC light, a battery gauge, a date and
clock stamp and a running tape counter, in blocky white type with a hard
shadow, framed by viewfinder corner brackets."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

MONTHS = ('JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC')


def timecode(t, fps=30):
    """Seconds `t` as a tape counter `HH:MM:SS:FF`, `FF` the frame within
    the second at `fps`."""
    f = max(0, int(round(t * fps)))
    s, ff = divmod(f, fps)
    m, ss = divmod(s, 60)
    hh, mm = divmod(m, 60)
    return f'{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}'


def clock(seconds):
    """Seconds since midnight as a 12-hour camcorder clock, `10:42:07 PM`."""
    s = int(seconds) % 86400
    h, rest = divmod(s, 3600)
    m, ss = divmod(rest, 60)
    return f'{(h - 1) % 12 + 1:2d}:{m:02d}:{ss:02d} {"AM" if h < 12 else "PM"}'


def _osd_text(cv, text, font, x, y, color, shadow, u, alpha):
    """One OSD string from its top-left with a hard offset shadow. Returns its width."""
    vb.text.draw(cv, [text], font, x + 3 * u, y + 3 * u, shadow, alpha=0.85 * alpha)
    vb.text.draw(cv, [text], font, x, y, color, alpha=alpha)
    return vb.text.measure(text, font)


def camcorder_overlay(cv, t, start=0.0, date=(1994, 10, 22), time_of_day=22 * 3600 + 42 * 60,
                      fps=30, battery=0.75, color='#f4f4f0', rec='#ff2a1f', shadow='#000000',
                      brackets=True, alpha=1.0):
    """Draw a camcorder's on-screen display over whatever is already on `cv`,
    at film time `t` seconds: a REC light blinking once a second (top left),
    a battery gauge `battery` (0 -> 1) full (top right), the `date`
    `(year, month, day)` stamp and a clock running on from `time_of_day`
    seconds after midnight (bottom left), and the tape counter `HH:MM:SS:FF`
    counting from `start` seconds at `fps` (bottom right). Everything scales
    with the canvas; `alpha` fades the whole display.

    In a film, draw the shot first, then `camcorder_overlay(cv, f / fps)`."""
    w, h = cv.width, cv.height
    u = h / 540
    m = 34 * u
    big, small = demo.mono(30 * u, 800), demo.mono(24 * u, 800)
    lh = vb.text.line_height(big)
    if brackets:  # viewfinder corners
        arm = 46 * u
        for cx, cy, sx, sy in ((m * 0.5, m * 0.5, 1, 1), (w - m * 0.5, m * 0.5, -1, 1),
                               (m * 0.5, h - m * 0.5, 1, -1), (w - m * 0.5, h - m * 0.5, -1, -1)):
            for dx, dy, col, a in ((2 * u, 2 * u, shadow, 0.6), (0, 0, color, 0.9)):
                cv.line(cx + dx, cy + dy, cx + dx + sx * arm, cy + dy, col, width=3 * u, alpha=a * alpha)
                cv.line(cx + dx, cy + dy, cx + dx, cy + dy + sy * arm, col, width=3 * u, alpha=a * alpha)
    # REC: the dot is lit for the first 0.6 s of every second
    x, y = m + 18 * u, m + 12 * u
    r = 11 * u
    if (t % 1.0) < 0.6:
        cv.sector(x + r + 2 * u, y + lh / 2 + 2 * u, r, 0, 2 * math.pi, shadow, alpha=0.8 * alpha)
        cv.sector(x + r, y + lh / 2, r, 0, 2 * math.pi, rec, alpha=alpha)
    _osd_text(cv, 'REC', big, x + 2 * r + 12 * u, y, color, shadow, u, alpha)
    # battery gauge with a nub and four cells
    bw, bh = 64 * u, lh * 0.62
    bx, by = w - m - 18 * u - bw, y + (lh - bh) / 2
    for dx, col, a in ((3 * u, shadow, 0.8), (0, color, 1.0)):
        cv.outline(bx + dx, by + dx, bw, bh, col, width=3 * u, alpha=a * alpha)
        cv.rect(bx + bw + dx, by + bh * 0.3 + dx, 5 * u, bh * 0.4, col, alpha=a * alpha)
    cells = max(0, min(4, math.ceil(vb.clamp01(battery) * 4)))
    cw = (bw - 6 * u - 3 * 3 * u) / 4
    for i in range(cells):
        cv.rect(bx + 3 * u + i * (cw + 3 * u), by + 3 * u, cw, bh - 6 * u, color, alpha=alpha)
    _osd_text(cv, 'SP', small, bx - 60 * u, y + (lh - vb.text.line_height(small)) / 2, color, shadow, u, alpha)
    # date and clock stamp, bottom left
    year, month, day = date
    by0 = h - m - 12 * u - 2 * lh
    _osd_text(cv, f'{MONTHS[month - 1]} {day:2d} {year}', big, m + 18 * u, by0, color, shadow, u, alpha)
    _osd_text(cv, clock(time_of_day + t), big, m + 18 * u, by0 + lh, color, shadow, u, alpha)
    # tape counter, bottom right
    tc = timecode(start + t, fps)
    tw = vb.text.measure(tc, big)
    _osd_text(cv, tc, big, w - m - 18 * u - tw, by0 + lh, color, shadow, u, alpha)
    cv.mark('timecode', w - m - 18 * u - tw, by0 + lh, tw, lh)


def _footage(cv, t):
    """The shot under the display: the sample photo on a slow handheld drift,
    dimmed and warmed a touch like tape."""
    img = demo.photo()
    x, y, bw, bh = vb.Box.of(cv).cover(img.w, img.h)
    s = 1.12
    dx = -bw * 0.05 * math.sin(t * 0.9) + 6 * math.sin(t * 7.3)
    dy = 5 * math.sin(t * 5.1 + 1)
    cv.image(img, x - bw * (s - 1) / 2 + dx, y - bh * (s - 1) / 2 + dy, bw * s, bh * s)
    cv.fill('#3a2a10', alpha=0.18)
    for row in range(0, cv.height, 4):  # faint interlace lines
        cv.rect(0, row, cv.width, 1, '#000000', alpha=0.12)


def draw(n, cv):
    t = n / demo.FPS
    _footage(cv, t)
    camcorder_overlay(cv, t, start=3 * 60 + 41.5, alpha=demo.phase(n, 0.0, 0.25))


TECHNIQUE = Technique(
    id='camcorder-timecode-overlay',
    name='Camcorder timecode overlay',
    family='vfx',
    group='VHS & tape',
    aliases=('camcorder OSD', 'home video overlay', 'REC overlay', 'VHS date stamp', 'viewfinder overlay'),
    definition='A home video camera\'s display sits over the shot: a blinking red REC light, a battery '
               'icon, a date and time stamp and a tape counter ticking off frames in chunky white digits.',
    phrasings=('make it look like it was filmed on an old camcorder with REC and the date in the corner',
               'put a home-movie viewfinder over the footage with a running counter',
               'add that 90s video camera overlay with the blinking record dot and timestamp'),
    related=('timecode-counter', 'keystroke-overlay', 'fire-overlay', 'frame-delay-echo',
             'video-clipped-inside-letterforms', 'freeze-frame'),
    api=('videobuilder.techniques.vfx.camcorder_timecode_overlay.camcorder_overlay',
         'videobuilder.techniques.vfx.camcorder_timecode_overlay.timecode',
         'videobuilder.techniques.vfx.camcorder_timecode_overlay.clock'),
    demo=lambda: demo.film(draw),
)
