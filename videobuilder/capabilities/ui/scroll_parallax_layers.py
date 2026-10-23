"""Scroll Parallax Layers: a page scrolls up and its layers move at different
rates -- the backdrop barely drifts, the headline lags behind, the content
moves one-for-one with the scroll -- so the flat page reads as deep.

`videobuilder.parallax` does the sideways, tiled version for a camera pan;
this is the vertical one for a scrolling page, where each layer is drawn
once in page coordinates and shifted by its share of the scroll."""
import videobuilder as vb
from videobuilder import parallax, paths

from .. import _demo as demo
from ..schema import Capability


def scroll_offset(scroll, rate):
    """How far (px, negative is up) a layer moving at `rate` sits when the
    page has scrolled `scroll` px: 0 is pinned, 1 moves with the content,
    under 1 lags behind as if further away, over 1 passes in front."""
    return -scroll * rate


def draw_scroll_layers(cv, layers, scroll):
    """Draw `layers`, a sequence of `(rate, draw)` listed back to front, with
    the page scrolled `scroll` px. Each `draw(cv)` paints its layer in page
    coordinates (y 0 at the top of the unscrolled page) and is shifted up by
    `scroll_offset(scroll, rate)`."""
    for rate, draw_layer in layers:
        with cv.layer(dy=scroll_offset(scroll, rate)):
            draw_layer(cv)


SCROLL = 420  # px the demo page scrolls
# The hills (from page y 440) and cards (from 655) start low enough that at the
# full scroll they still sit below the headline (rate 0.3), which ends near y 164.
RIDGE = parallax.ridge(demo.W, 120, seed=4) + [(demo.W, 900), (0, 900)]


def _sky(cv):
    demo.dot(cv, demo.W * 0.72, 150, r=90, color=demo.TEAL, alpha=0.35)
    for i, (x, y) in enumerate(((120, 90), (200, 250), (520, 70), (860, 260), (430, 330), (700, 420))):
        demo.dot(cv, x, y, r=3 + i % 2, color=demo.MUTED, alpha=0.7)


def _hills(cv):
    paths.draw(cv, [(x, 440 + y) for x, y in RIDGE], demo.LINE, fill=True)


def _headline(cv):
    demo.word(cv, 'Scroll down', demo.W / 2, 220, size=84)
    demo.word(cv, 'layers drift at their own pace', demo.W / 2, 290, size=26, color=demo.MUTED, weight=500)


def _content(cv):
    for i, x in enumerate((demo.W / 2 - 290, demo.W / 2, demo.W / 2 + 290)):
        demo.card(cv, x, 730 + 30 * (i % 2), w=240, h=150, color=(demo.ACCENT, demo.TEAL, demo.ACCENT)[i])
    demo.card(cv, demo.W / 2, 940, w=820, h=150, color='#3b3f4a')


LAYERS = ((0.1, _sky), (0.3, _headline), (0.55, _hills), (1.0, _content))


def draw(n, cv):
    p = vb.ease_in_out_quart(demo.phase(n, 0.4, 2.6))
    scroll = SCROLL * p
    draw_scroll_layers(cv, LAYERS, scroll)
    track = demo.H - 40  # a scrollbar, so it reads as a page being scrolled
    cv.rect(demo.W - 14, 20, 6, track, demo.LINE, radius=3)
    cv.rect(demo.W - 14, 20 + (track - 180) * p, 6, 180, demo.MUTED, radius=3)


CAPABILITY = Capability(
    id='scroll-parallax-layers',
    name='Scroll parallax layers',
    family='ui',
    group='Scroll',
    aliases=('scroll parallax', 'parallax scrolling', 'scroll-linked parallax'),
    definition='As a page scrolls, its background, headline and content each move at their own speed, '
               'the far layers lagging behind the near ones so the page feels deep.',
    phrasings=('the background moves slower than the page when you scroll',
               'scroll the landing page with the layers sliding at different speeds',
               'give the scroll some depth, hero image lagging behind the content'),
    related=('parallax-layers', 'parallax-slide', 'pointer-parallax-layers', 'parallax-letter-layers',
             'layered-fog-bands', 'parallax-marquee-rows'),
    api=('videobuilder.capabilities.ui.scroll_parallax_layers.draw_scroll_layers',
         'videobuilder.capabilities.ui.scroll_parallax_layers.scroll_offset'),
    demo=lambda: demo.film(draw),
)
