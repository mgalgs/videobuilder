"""Letter roll: on hover, each letter of a label slides up out of its own
slot while a fresh copy slides up from below to take its place, the letters
going one after another across the word."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def roll_progress(i, count, p, stagger=0.5):
    """Progress 0 -> 1 of letter `i` of `count` when the whole roll is at `p`.
    The first letter starts at 0 and the last at `stagger`, each taking
    `1 - stagger` of the roll."""
    start = stagger * i / max(count - 1, 1)
    return vb.clamp01((p - start) / (1 - stagger))


def draw_roll(cv, text, font, x, y, p, color, rolled_color=None, stagger=0.5, ease=vb.ease_in_out_quart):
    """Draw `text` from its top-left (x, y) part-way through a letter roll at
    progress `p` (0 -> 1). Each letter is clipped to its own slot: the copy
    in `color` leaves upwards while one in `rolled_color` (default `color`)
    rises from below, letter by letter (`stagger`, see `roll_progress`).
    To roll back, call again with the colours swapped. Returns the Box of the line."""
    lh = vb.text.line_height(font)
    rolled_color = color if rolled_color is None else rolled_color
    left = x
    for i, ch in enumerate(text):
        adv = vb.text.measure(ch, font)
        if not ch.isspace():
            shift = ease(roll_progress(i, len(text), p, stagger)) * lh
            with cv.clip(left, y, adv, lh):
                if shift < lh:
                    vb.text.draw(cv, [ch], font, left, y - shift, color)
                if shift > 0:
                    vb.text.draw(cv, [ch], font, left, y + lh - shift, rolled_color)
        left += adv
    return vb.Box(x, y, left - x, lh)


def _cursor(cv, x, y, s=1.6):
    """A plain arrow pointer with its tip at (x, y)."""
    pts = [(0, 0), (0, 22), (6, 17), (10, 26), (14, 24), (10, 16), (17, 16)]
    c = cv.ctx
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    c.move_to(*pts[0])
    for pt in pts[1:]:
        c.line_to(*pt)
    c.close_path()
    c.set_source_rgba(*vb.rgba(demo.INK))
    c.fill_preserve()
    c.set_source_rgba(0, 0, 0, 0.8)
    c.set_line_width(1.4)
    c.stroke()
    c.restore()


def draw(n, cv):
    f = demo.font(150, 900)
    text = 'MOTION'
    w, h = vb.text.block_size([text], f)
    x, y = (demo.W - w) / 2, (demo.H - h) / 2
    t = n / demo.FPS
    if t < 1.9:  # hovered: roll into the accent
        box = draw_roll(cv, text, f, x, y, demo.phase(n, 0.75, 1.55), demo.INK, demo.ACCENT)
    else:        # left: roll back to ink
        box = draw_roll(cv, text, f, x, y, demo.phase(n, 1.95, 2.75), demo.ACCENT, demo.INK)
    cv.mark('text', *box)
    # the pointer glides onto the word's end, rests, then drifts away
    rest = (x + w - 40, y + h * 0.6)
    arrive = vb.ease_out_expo(demo.phase(n, 0.1, 0.75))
    leave = vb.ease_in_expo(demo.phase(n, 1.7, 2.1))
    cx = rest[0] + 260 * (1 - arrive) + 220 * leave
    cy = rest[1] + 180 * (1 - arrive) + 200 * leave
    _cursor(cv, cx, cy)


CAPABILITY = Capability(
    id='letter-roll',
    name='Letter roll',
    family='ui',
    group='Text & type',
    aliases=('text roll', 'letter shuffle', 'roll on hover'),
    definition='When the pointer lands on a label, its letters scroll up and away one after another, '
               'each replaced by an identical letter rising into its slot from underneath.',
    phrasings=('make the button text roll up letter by letter when I hover it',
               'the word flips over vertically, one character at a time, on mouse-over',
               'each letter slides up and a new copy slides in from below'),
    related=('letter-sort-animation', 'grid-reflow-shuffle', 'word-carousel-rotate', 'rotating-circular-text',
             'character-rotate-in', 'character-drop'),
    api=('videobuilder.capabilities.ui.letter_roll.draw_roll',
         'videobuilder.capabilities.ui.letter_roll.roll_progress'),
    demo=lambda: demo.film(draw),
)
