"""Seven-segment display: each digit is drawn from seven bars that light up
or go dark, the way a calculator or alarm clock shows numbers, with the dark
bars still faintly visible behind the lit ones."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

# Segments a-g: a top, b upper right, c lower right, d bottom, e lower left,
# f upper left, g middle.
SEGMENTS = {
    '0': 'abcdef', '1': 'bc', '2': 'abdeg', '3': 'abcdg', '4': 'bcfg', '5': 'acdfg', '6': 'acdefg',
    '7': 'abc', '8': 'abcdefg', '9': 'abcdfg', '-': 'g', '_': 'd', ' ': '',
    'A': 'abcefg', 'b': 'cdefg', 'C': 'adef', 'c': 'deg', 'd': 'bcdeg', 'E': 'adefg', 'F': 'aefg',
    'H': 'bcefg', 'h': 'cefg', 'L': 'def', 'o': 'cdeg', 'P': 'abefg', 'r': 'eg', 'U': 'bcdef', 'u': 'cde',
}


def segments(ch):
    """The lit segments ('a'-'g') for `ch`, as a string; unknown characters
    try the other case, then light nothing."""
    return SEGMENTS.get(ch, SEGMENTS.get(ch.upper(), SEGMENTS.get(ch.lower(), '')))


def _bars(x, y, h, thick):
    """Each segment's rectangle (x, y, w, h) for a digit cell `h` tall with its top-left at (x, y)."""
    w, t, gap = h * 0.5, thick, thick * 0.18
    half = h / 2
    horiz = w - t - 2 * gap
    vert = half - t / 2 - 2 * gap
    hx = x + t / 2 + gap
    return {
        'a': (hx, y, horiz, t),
        'g': (hx, y + half - t / 2, horiz, t),
        'd': (hx, y + h - t, horiz, t),
        'f': (x, y + t / 2 + gap, t, vert),
        'b': (x + w - t, y + t / 2 + gap, t, vert),
        'e': (x, y + half + gap, t, vert),
        'c': (x + w - t, y + half + gap, t, vert),
    }


def digit_width(h):
    """The width of one digit cell `h` tall."""
    return h * 0.5


def draw_digit(cv, ch, x, y, h, color, off=None, prev=None, p=1.0, thick=None, off_alpha=0.12):
    """Draw `ch` as a seven-segment digit `h` tall, top-left at (x, y). Unlit
    bars are drawn in `off` (default `color` at `off_alpha`) so the eight
    shape stays readable. Give `prev` and `p` (0 -> 1) to switch from the
    previous character: bars turning on fade up, bars turning off fade down.
    Returns the digit's Box."""
    t = thick or h * 0.1
    was, now = set(segments(prev) if prev is not None else segments(ch)), set(segments(ch))
    p = vb.clamp01(p)
    for name, (bx, by, bw, bh) in _bars(x, y, h, t).items():
        lit = (name in now) * p + (name in was) * (1 - p)
        if off is None:
            cv.rect(bx, by, bw, bh, color, radius=t / 2, alpha=off_alpha)
        else:
            cv.rect(bx, by, bw, bh, off, radius=t / 2)
        if lit > 0:
            cv.rect(bx, by, bw, bh, color, radius=t / 2, alpha=lit)
    return vb.Box(x, y, digit_width(h), h)


def draw_display(cv, text, x, y, h, color, prev=None, p=1.0, spacing=None, **kw):
    """Draw `text` as a row of seven-segment digits `h` tall from top-left
    (x, y); ':' draws a narrow colon. `prev` (same length) and `p` cross-fade
    each digit from its old character, as in `draw_digit`. `kw` goes to
    `draw_digit`. Returns the Box of the row."""
    gap = h * 0.14 if spacing is None else spacing
    left = x
    for i, ch in enumerate(text):
        if ch == ':':
            r = h * 0.055
            for cy in (y + h * 0.3, y + h * 0.7):
                cv.rect(left, cy - r, 2 * r, 2 * r, color, radius=r)
            left += 2 * r + gap
            continue
        old = prev[i] if prev is not None and i < len(prev) else None
        draw_digit(cv, ch, left, y, h, color, prev=old, p=p, **kw)
        left += digit_width(h) + gap
    return vb.Box(x, y, left - gap - x, h)


def display_width(text, h, spacing=None):
    """The width `draw_display` takes for `text` at height `h`."""
    gap = h * 0.14 if spacing is None else spacing
    return sum(h * 0.11 if ch == ':' else digit_width(h) for ch in text) + gap * (len(text) - 1)


STEP = 3  # frames per displayed value in the demo
FADE = 2  # frames a bar takes to switch
STEPS = 18  # values in the count; it lands at frame 12 + STEP * STEPS and holds


def _value(k):
    """The demo counter after `k` steps: races up, then slows to land on 2048."""
    q = vb.clamp01(k / STEPS)
    return round(2048 * (1 - (1 - q) ** 3))


def draw(n, cv):
    k = max(0, n - 12) // STEP
    now, was = f'{_value(k):04d}', f'{_value(k - 1):04d}' if k else '    '
    p = ((max(0, n - 12) % STEP) + 1) / FADE if n >= 12 else 0.0
    h = 300
    w = display_width(now, h)
    x, y = (demo.W - w) / 2, (demo.H - h) / 2
    pad = 50
    cv.rect(x - pad, y - pad, w + 2 * pad, h + 2 * pad, '#0c0d10', radius=24)
    box = draw_display(cv, now, x, y, h, '#ffc53d', prev=was, p=p)
    cv.mark('display', *box)


CAPABILITY = Capability(
    id='seven-segment-display',
    name='Seven-segment display',
    family='typography',
    group='Mechanical display',
    aliases=('LED segment digits', 'segment reveal', 'digital clock digits', 'LCD digits'),
    definition='Numbers are built from seven straight bars per digit, and changing a number simply '
               'switches some bars on and others off, like an alarm clock readout.',
    phrasings=('make the numbers look like a digital clock',
               'show the counter in those blocky calculator digits',
               'an LED readout where the segments flick on and off as it counts'),
    related=('decimal-counter-with-formatting', 'number-count-down', 'circular-clip-reveal',
             'pixelation-reveal', 'segmented-control-slide', 'funnel-stage-reveal'),
    api=('videobuilder.capabilities.typography.seven_segment_display.draw_display',
         'videobuilder.capabilities.typography.seven_segment_display.draw_digit',
         'videobuilder.capabilities.typography.seven_segment_display.display_width',
         'videobuilder.capabilities.typography.seven_segment_display.segments'),
    demo=lambda: demo.film(draw),
)
