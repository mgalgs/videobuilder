"""Page Load Sequence: a screen builds itself in a set order as it opens --
the navigation bar drops in, then the headline, then the button, then the
content cards rise one after another -- instead of appearing all at once."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def load_progress(i, count, p, overlap=0.55):
    """Progress 0 -> 1 of part `i` of `count` at overall progress `p`. Parts
    start in order, each lasting `span` of the whole; `overlap` (0..1) is how
    much a part's run shares with the next one's (0: strictly one after
    another, near 1: almost together). The last part ends at `p == 1`."""
    if count <= 1:
        return vb.clamp01(p)
    span = 1 / (1 + (count - 1) * (1 - overlap))
    return vb.clamp01((p - i * span * (1 - overlap)) / span)


def page_load_sequence(cv, parts, p, overlap=0.55, ease=vb.ease_out_quint):
    """Draw `parts` loading in order at progress `p` (0 -> 1). Each part is
    `(draw, dx, dy)`: `draw(cv)` draws it at rest, and it arrives from an
    offset of (dx, dy) pixels, fading up as it slides home, eased by `ease`.
    Parts are drawn in list order, so list them as they should arrive (the
    page's frame first, its content after). `overlap` goes to `load_progress`.

    In a film, pass the shot's own progress, e.g.
    `page_load_sequence(cv, [(nav, 0, -40), (hero, 0, 30), (cards, 0, 60)], vb.clamp01(f / (1.2 * fps)))`."""
    for i, (draw, dx, dy) in enumerate(parts):
        q = load_progress(i, len(parts), p, overlap)
        if q <= 0:
            continue
        e = ease(q)
        with cv.layer(opacity=vb.clamp01(q * 2.5), dx=dx * (1 - e), dy=dy * (1 - e)):
            draw(cv)


# The demo: a mock web page inside a browser window.
X, Y, PW, PH = 90, 50, demo.W - 180, demo.H - 100   # the page area
PAGE = '#1d1f26'


def window(cv):
    cv.shadow(X, Y, PW, PH, radius=14, dy=12, blur=30, color=(0, 0, 0, 0.5))
    cv.rect(X, Y, PW, PH, PAGE, radius=14)
    for k, c in enumerate(('#ef5b4c', '#f0b44c', '#4fc3b0')):
        demo.dot(cv, X + 22 + 18 * k, Y + 18, 5, color=c)


def nav(cv):
    y = Y + 36
    cv.rect(X, y, PW, 46, demo.LINE)
    demo.dot(cv, X + 34, y + 23, 11, color=demo.ACCENT)
    for k in range(4):
        cv.rect(X + PW - 330 + 78 * k, y + 19, 56, 8, demo.MUTED, radius=4)
    cv.mark('nav', X, y, PW, 46)


def headline(cv):
    box = demo.word(cv, 'Welcome home', demo.W / 2, Y + 140, size=44)
    cv.rect(demo.W / 2 - 170, Y + 180, 340, 10, demo.MUTED, radius=5, alpha=0.7)
    cv.mark('headline', *box)


def button(cv):
    cv.rect(demo.W / 2 - 80, Y + 210, 160, 40, demo.ACCENT, radius=20)
    demo.word(cv, 'Get started', demo.W / 2, Y + 230, size=18, weight=700)


def card_at(k):
    return lambda cv: demo.card(cv, demo.W / 2 + (k - 1) * 240, Y + 350, w=210, h=120,
                                color=(demo.TEAL, '#5b6cf0', demo.ACCENT)[k])


PARTS = [(window, 0, 0), (nav, 0, -40), (headline, 0, 36), (button, 0, 36)] + \
        [(card_at(k), 0, 70) for k in range(3)]


def draw(n, cv):
    page_load_sequence(cv, PARTS, demo.phase(n, 0.3, 2.4), overlap=0.45)


CAPABILITY = Capability(
    id='page-load-sequence',
    name='Page load sequence',
    family='ui',
    group='Page transitions',
    aliases=('load-in animation', 'intro choreography', 'entrance sequence', 'staggered page load'),
    definition='When a screen opens, its pieces arrive one after another in a planned order, '
               'the frame and menu first and the content after, each sliding a little and fading into place.',
    phrasings=('make the website build itself piece by piece when it opens',
               'have the menu, then the title, then the cards come in one at a time as the page loads',
               'animate the page elements in on load instead of showing everything at once'),
    related=('scrollytelling-step-sequence', 'staging', 'page-turn', 'staggered-cascade-reveal',
             'scroll-driven-text-reveal', 'staged-onboarding-walkthrough'),
    api=('videobuilder.capabilities.ui.page_load_sequence.page_load_sequence',
         'videobuilder.capabilities.ui.page_load_sequence.load_progress'),
    demo=lambda: demo.film(draw),
)
