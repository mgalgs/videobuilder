"""Shared-element transition: one element that both screens have in common (a
thumbnail, an avatar, a card) flies and resizes from its place in the old
screen to its place in the new one, while everything around it crossfades."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def shared_element_transition(cv, a, b, p, element, start, end, radius=(0, 0), ease=vb.ease_in_out_quart,
                              fade=(0.15, 0.75), lift=0.35):
    """Draw the transition at progress `p` (0 -> 1). `a(cv)` and `b(cv)` draw
    the two screens *without* the shared element; `element(cv, box, radius)`
    draws it filling `box` (x, y, w, h) with that corner radius. The element
    travels from `start` to `end` on `ease`, its corner radius going from
    `radius[0]` to `radius[1]`, lifted by a shadow (`lift` its opacity at the
    midpoint) while in flight; `b` fades in over `a` across the `fade` span of `p`.

    In a film, call it while both screens are live in an overlap, with the
    element's two boxes taken from each screen's layout, e.g.
    `shared_element_transition(cv, grid_rest, detail_rest, f / overlap_frames, thumb, slot_box, header_box)`."""
    e = ease(vb.clamp01(p))
    a(cv)
    with cv.layer(opacity=vb.clamp01((p - fade[0]) / (fade[1] - fade[0]))):
        b(cv)
    box = tuple(s + (t - s) * e for s, t in zip(start, end))
    r = radius[0] + (radius[1] - radius[0]) * e
    arc = 4 * e * (1 - e)  # 0 at both ends, 1 midway: the element rises off the page and settles back
    if arc > 0:
        cv.shadow(*box, radius=r, dy=18 * arc, blur=40 * arc, color=(0, 0, 0, lift * arc))
    element(cv, box, r)


# ---- demo: a grid of thumbnails opens one into a detail screen ----
COLS, ROWS, TW, TH, GAP, TOP = 3, 2, 220, 130, 28, 150
X0 = (demo.W - (COLS * TW + (COLS - 1) * GAP)) / 2
PICK = (1, 1)  # (col, row) of the thumbnail that opens
SLOT = (X0 + PICK[0] * (TW + GAP), TOP + PICK[1] * (TH + GAP), TW, TH)
HEADER = (0, 0, demo.W, 290)
PAPER = '#e9e6df'


def _photo(cv, box, r):
    cv.view(demo.photo(), box, radius=r)


def _grid(cv):
    cv.fill(demo.BG)
    vb.text.draw(cv, ['Library'], demo.font(36, 800), X0, 72, demo.INK)
    tints = (demo.ACCENT, demo.TEAL, demo.LINE, demo.TEAL, None, demo.ACCENT)
    for i, tint in enumerate(tints):
        if tint:
            col, row = i % COLS, i // COLS
            cv.rect(X0 + col * (TW + GAP), TOP + row * (TH + GAP), TW, TH, tint, radius=14, alpha=0.85)


def _detail(cv):
    cv.fill(PAPER)
    vb.text.draw(cv, ['Harbour at dusk'], demo.font(40, 800), 60, 324, demo.BG)
    for i, (w, a) in enumerate(((520, 0.55), (440, 0.4), (480, 0.4))):
        cv.rect(60, 400 + i * 34, w, 14, demo.MUTED, radius=7, alpha=a)


def _demo():
    def scene_a(cv):
        _grid(cv)
        _photo(cv, SLOT, 14)

    def scene_b(cv):
        _detail(cv)
        _photo(cv, HEADER, 0)

    def transition(cv, a, b, p):
        shared_element_transition(cv, _grid, _detail, p, _photo, SLOT, HEADER, radius=(14, 0))

    return demo.two_scenes(transition, start=1.3, length=1.3, a=scene_a, b=scene_b)


CAPABILITY = Capability(
    id='shared-element-transition',
    name='Shared-element transition',
    family='transitions',
    group='Interface and Views',
    aliases=('hero transition', 'hero animation', 'magic move', 'container transform', 'matched geometry'),
    definition='An element present on both screens glides and resizes from where it sits on the first screen '
               'to where it sits on the second, while the rest of the view crossfades around it.',
    phrasings=('tap the thumbnail and have it grow into the big header image on the next screen',
               'keep the same picture on screen and morph it into its new spot as the page changes',
               'carry the card over from the list view into the detail view'),
    related=('palette-shift-transition', 'split-screen-transition', 'icon-state-morph', 'zoom-through',
             'pixelate-transition', 'theme-swap-crossfade'),
    api=('videobuilder.capabilities.transitions.shared_element_transition.shared_element_transition',),
    demo=_demo,
)
