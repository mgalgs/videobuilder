"""Perspective Crawl: a block of text laid flat on a plane that tilts back
from the viewer, sliding up and away so each line shrinks toward a horizon
and fades out there.

Cairo only does affine transforms, so the plane is drawn in thin horizontal
bands: each band of the screen shows one slice of the flat page, at the
width and height that slice has at its depth. With bands a pixel or two
tall the seams don't show, and the result is a true perspective.
"""
from functools import lru_cache

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def crawl_page(lines, font, width, color, align='center', scale=1.0):
    """The flat page a crawl slides: `lines` drawn top-down in `font` and
    `color`, aligned within `width`, on a transparent `vb.Canvas` as tall as
    the text. Draw it once and reuse it every frame; `scale` is its pixel
    density (match the film canvas's `scale_factor()` for crisp text)."""
    lines = list(lines)
    h = vb.text.line_height(font) * len(lines)
    page = vb.Canvas(width, h, scale=scale)
    vb.text.draw(page, lines, font, 0, 0, color, align=align, width=width)
    return page


def draw_crawl(cv, page, scroll, horizon=None, near=None, depth=None, cx=None,
               fade=(0.12, 0.4), step=1.5, alpha=1.0):
    """Draw `page` (a canvas, e.g. from `crawl_page`) lying on a plane that
    recedes from the bottom of the frame to a horizon. `scroll` is how far
    the page has travelled, in page px: page row `scroll` sits at the near
    edge, rows above it lie further away, rows below it are not yet on.
    Animate `scroll` upward to make the text crawl away.

    `horizon`: the screen y the plane vanishes to (default 18% down).
    `near`: the screen y of the near edge, where the page is full size
    (default the bottom of the frame). `depth`: how deep the plane is in page
    px -- smaller tilts it harder (default the frame width). `cx`: the
    vanishing point's x (default the centre). The text fades out between
    the scales in `fade` (as fractions of full size). `step` is the band
    height in output pixels."""
    W = cv.width
    horizon = cv.height * 0.18 if horizon is None else horizon
    near = cv.height if near is None else near
    depth = W if depth is None else depth
    cx = W / 2 if cx is None else cx
    f0, f1 = fade
    ps = page.scale
    band = step / max(cv.scale_factor(), 1e-6)

    def row(y):  # (page row, scale) at screen y
        s = (y - horizon) / (near - horizon)
        return scroll - (depth / s - depth), s

    c = cv.ctx
    y = horizon + f0 * (near - horizon)  # nothing shows above the fully-faded scale
    while y < near:
        yb = min(near, y + band)
        va, sa = row(y)
        vb_, sb = row(yb)
        if vb_ > 0 and va < page.height:
            s = (sa + sb) / 2
            k = (yb - y) / (vb_ - va)
            a = alpha * vb.clamp01((s - f0) / (f1 - f0))
            if a > 0:
                c.save()
                c.rectangle(0, y, W, yb - y)
                c.clip()
                c.translate(cx - s * page.width / 2, y - k * va)
                c.scale(s / ps, k / ps)
                c.set_source_surface(page.surface, 0, 0)
                c.paint_with_alpha(a)
                c.restore()
        y = yb


TEXT = ('CHAPTER ONE', '', 'THE LONG RENDER', '',
        'Far across the timeline,', 'a lone renderer works', 'through the night to',
        'finish every frame of', 'the cut before the', 'deadline arrives. Each', 'scene it completes',
        'drifts off into the', 'distance, never to be', 'seen again....')


@lru_cache(maxsize=4)
def _page(scale):
    return crawl_page(TEXT, demo.font(46, 700), 760, '#f2c94c', scale=max(scale, 0.25))


def _stars(cv):
    for i in range(40):
        x, y = (i * 389) % demo.W, (i * 211 + i * i * 7) % demo.H
        demo.dot(cv, x, y, r=1.2 + (i % 3) * 0.5, color=demo.INK, alpha=0.35 + 0.15 * (i % 3))


def draw(n, cv):
    _stars(cv)
    page = _page(round(cv.scale_factor(), 3))
    draw_crawl(cv, page, 420 + 300 * n / demo.FPS, depth=560)
    cv.mark('text', demo.W / 2 - 380, demo.H * 0.25, 760, demo.H * 0.75)


TECHNIQUE = Technique(
    id='perspective-crawl',
    name='Perspective crawl',
    family='typography',
    group='Credits and crawls',
    aliases=('opening crawl', 'space crawl', 'receding text scroll', '3D text crawl'),
    definition='Lines of text lie on a plane tilted away from the viewer and glide up into the distance, '
               'shrinking toward a vanishing point and fading out as they go.',
    phrasings=('text that scrolls up and away into space like an epic movie intro',
               'a paragraph on a tilted floor drifting off toward the horizon',
               'make the story text slide back into the distance in perspective'),
    related=('perspective-tunnel-type', 'word-flip-in', 'isometric-view', 'scroll-driven-text-reveal',
             'infinite-zoom-tunnel', 'tilt'),
    api=('videobuilder.techniques.typography.perspective_crawl.draw_crawl',
         'videobuilder.techniques.typography.perspective_crawl.crawl_page'),
    demo=lambda: demo.film(draw),
)
