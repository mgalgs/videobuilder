"""Scrollytelling Step Sequence: a column of text steps scrolls past a pinned
graphic, and as each step reaches the middle of the view the graphic
highlights the part that step talks about."""
import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ..schema import Technique


def step_weights(scroll, count, edge=0.5, soft=0.2):
    """How active each of `count` steps is (0 -> 1) at `scroll`, measured in
    steps (0 is the first step centred on the trigger line, 1 the second, ...).
    A step is fully on while it is within `edge - soft` of the line and fades
    out by `edge`, so the hand-over between neighbours is quick and clean."""
    out = []
    for i in range(count):
        t = vb.clamp01((edge - abs(scroll - i)) / soft)
        out.append(t * t * (3 - 2 * t))
    return out


def scroll_holds(t, count, hold=0.5, move=0.7, start=0.0):
    """A reader's scroll position (in steps) at `t` seconds: rest on each step
    for `hold` seconds, then glide to the next over `move` seconds."""
    t -= start
    for i in range(count - 1):
        if t < hold:
            return float(i)
        if t < hold + move:
            return i + vb.ease_in_out_quart((t - hold) / move)
        t -= hold + move
    return float(count - 1)


def draw_step(cv, step, x, y, w, active, index):
    """One text step from its top-left (x, y): a number, a title and two bars
    of body copy, with a rule down its left edge. `active` (0 -> 1) brightens
    it and lights the rule."""
    alpha = 0.3 + 0.7 * active
    cv.rect(x, y, 4, 110, demo.LINE, radius=2)
    cv.rect(x, y, 4, 110, demo.ACCENT, radius=2, alpha=active)
    vb.text.draw(cv, [f'{index + 1:02d}'], demo.mono(16, 700), x + 20, y + 2, demo.ACCENT, alpha=alpha)
    vb.text.draw(cv, [step], demo.font(28, 800), x + 20, y + 26, demo.INK, alpha=alpha)
    for k, frac in enumerate((0.9, 0.6)):
        cv.rect(x + 20, y + 76 + k * 18, (w - 20) * frac, 8, demo.MUTED, radius=4, alpha=alpha * 0.6)


def draw_scrollytelling(cv, box, steps, scroll, visual, gap=190, split=0.42):
    """A scrollytelling layout in `box`: `steps` (short titles) scroll up the
    left `split` of the box, `gap` px apart, past a trigger line at its middle;
    the right side stays pinned and is drawn by `visual(cv, panel_box, weights)`,
    where `weights[i]` is how active step i is. `scroll` is in steps (see
    `scroll_holds`). Returns the weights."""
    weights = step_weights(scroll, len(steps))
    x, y, w, h = box
    col = w * split
    mid = y + h / 2
    with cv.clip(x, y, col, h):
        for i, step in enumerate(steps):
            draw_step(cv, step, x + 28, mid - 55 + (i - scroll) * gap, col - 56, weights[i], i)
    cv.line(x + col, y + 16, x + col, y + h - 16, demo.LINE, width=1.5)
    visual(cv, vb.Box(x + col + 28, y + 28, w - col - 64, h - 56), weights)
    track = h - 32
    thumb = track / len(steps)
    cv.rect(x + w - 14, y + 16, 4, track, demo.LINE, radius=2)
    cv.rect(x + w - 14, y + 16 + scroll / max(1, len(steps) - 1) * (track - thumb), 4, thumb, demo.TEAL,
            radius=2)
    return weights


VALUES = (0.45, 0.9, 0.65)


def bars(cv, box, weights):
    """The demo's pinned graphic: a three-bar chart where the active step's
    bar turns accent and the others recede, with progress dots below."""
    x, y, w, h = box
    cv.rect(x, y, w, h, '#1b1d23', radius=16)
    base = y + h - 64
    bw = w / 7
    for i, (v, a) in enumerate(zip(VALUES, weights)):
        bx = x + bw * (1 + 2 * i)
        bh = (h - 110) * v
        cv.rect(bx, base - bh, bw, bh, kit.mix(demo.LINE, demo.ACCENT, a), radius=6)
        cv.rect(bx, base + 10, bw, 5, demo.ACCENT, radius=2.5, alpha=a)
    for i, a in enumerate(weights):
        demo.dot(cv, x + w / 2 + (i - 1) * 20, y + h - 26, r=5, color=kit.mix(demo.LINE, demo.ACCENT, a))
    cv.mark('visual', *box)


STEPS = ('Where it starts.', 'The big jump.', 'Where it lands.')


def draw(n, cv):
    box = vb.Box(60, 40, demo.W - 120, demo.H - 80)
    cv.rect(*box, '#17181e', radius=16)
    cv.outline(*box, demo.LINE, width=1.5, radius=16)
    with cv.clip(*box, 16):
        draw_scrollytelling(cv, box, STEPS, scroll_holds(n / demo.FPS, len(STEPS), hold=0.55, move=0.6,
                                                         start=0.15), bars)
    cv.mark('page', *box)


TECHNIQUE = Technique(
    id='scrollytelling-step-sequence',
    name='Scrollytelling step sequence',
    family='ui',
    group='Scroll',
    aliases=('scroll narrative', 'story scroll', 'scrollytelling', 'sticky graphic with steps'),
    definition='Short blocks of text scroll past a graphic that stays pinned in place, and each time a '
               'new block reaches the middle the graphic lights up the part that block describes.',
    phrasings=('as you scroll down, the chart highlights whatever the paragraph is talking about',
               'text steps scroll by on the left while the picture on the right stays put and changes',
               'a story page where each section scrolls in and spotlights a different piece of the graphic'),
    related=('scroll-driven-text-reveal', 'timeline-scroll', 'roll-up', 'page-load-sequence',
             'rolling-end-credits', 'perspective-crawl'),
    api=('videobuilder.techniques.ui.scrollytelling_step_sequence.draw_scrollytelling',
         'videobuilder.techniques.ui.scrollytelling_step_sequence.step_weights',
         'videobuilder.techniques.ui.scrollytelling_step_sequence.scroll_holds'),
    demo=lambda: demo.film(draw),
)
