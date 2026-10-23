"""View transition: the whole old view and the whole new view, each frozen as
a snapshot, cross-fade into each other, while any element the two views share
glides and resizes from where it sat in the old view to where it sits in the
new one."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

# The curve an interface uses for this by default: a quick start, a long soft settle.
EASE = vb.bezier(0.25, 0.1, 0.25, 1)


def view_transition(cv, a, b, p, shared=(), ease=EASE):
    """Draw the transition at progress `p` (0 -> 1): `a(cv)` with `b(cv)`
    fading in over it, then each shared element on top.

    `shared` is a sequence of `(from_box, to_box, draw)`: `draw(cv, box, t)`
    paints the element into `box`, an `(x, y, w, h)` eased from `from_box` to
    `to_box`, with `t` the eased progress (use it to cross-fade the element's
    own old and new look). `a` and `b` should leave the shared elements out,
    as the moving copy stands in for them.

    In a film, call it inside a scene overlap, e.g.
    `view_transition(cv, list_page, detail_page, new.f / overlap_frames, shared=[(thumb, hero, draw_photo)])`."""
    t = ease(vb.clamp01(p))
    a(cv)
    with cv.layer(opacity=t):
        b(cv)
    for from_box, to_box, draw in shared:
        box = vb.Box(*(f + (e - f) * t for f, e in zip(from_box, to_box)))
        draw(cv, box, t)


# ---- the demo: a gallery list page opening into a photo's detail page ----

W, H = demo.W, demo.H
THUMB = (60, 100, 240, 150)                       # the photo's card in the list
HERO = (0, 0, W, 330)                              # the same photo as the detail page's header
CARDS = ((480, 175), (780, 175), (180, 365), (480, 365), (780, 365))


def _photo(cv, box, t=0.0):
    cv.view(demo.photo(), box, radius=14 * (1 - t))
    cv.mark('photo', *box)


def list_page(cv, with_photo=True):
    cv.fill(demo.BG)
    cv.rect(0, 0, W, 72, '#1b1d22')
    demo.word(cv, 'Gallery', 120, 36, size=30)
    if with_photo:
        _photo(cv, THUMB)
    for i, (cx, cy) in enumerate(CARDS):
        demo.card(cv, cx, cy, w=240, h=150, color=(demo.TEAL, demo.ACCENT)[i % 2], alpha=0.9)


def detail_page(cv, with_photo=True):
    cv.fill('#e9e6df')
    if with_photo:
        _photo(cv, HERO, 1.0)
    demo.word(cv, 'Harbour at dusk', W / 2, 385, size=44, color=demo.BG)
    for i, w in enumerate((520, 440, 480)):
        cv.rect(W / 2 - 260, 430 + i * 30, w, 12, demo.MUTED, radius=6, alpha=0.7)


def _draw(n, cv):
    p = demo.phase(n, 1.4, 2.9)  # mid-blend at the gallery poster (2.1 s)
    if p <= 0:
        list_page(cv)
    elif p >= 1:
        detail_page(cv)
    else:
        view_transition(cv, lambda c: list_page(c, False), lambda c: detail_page(c, False), p,
                        shared=[(THUMB, HERO, _photo)])


CAPABILITY = Capability(
    id='view-transition',
    name='View transition',
    family='transitions',
    group='Interface and Views',
    aliases=('page view transition', 'snapshot transition', 'cross-document view transition',
             'shared element transition'),
    definition='One screen of an interface melts into the next as a cross-fade of the two whole views, '
               'while anything they share slides and resizes straight into its new place.',
    phrasings=('fade from one page of the app to the next like a browser page change',
               'tap a thumbnail and have it grow into the header of the detail page while the rest fades over',
               'move between two screens with a soft blend, keeping the shared picture in view'),
    related=('split-screen-transition', 'palette-shift-transition', 'zoom-through',
             'image-crossfade-slideshow', 'tab-panel-slide', 'theme-swap-crossfade'),
    api=('videobuilder.capabilities.transitions.view_transition.view_transition',),
    demo=lambda: demo.film(_draw),
)
