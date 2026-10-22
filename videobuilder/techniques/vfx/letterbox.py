"""Letterbox: solid bars close in from the top and bottom of the frame until
the visible picture has a wider, cinema-style aspect ratio."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def letterbox(cv, p=1.0, ratio=2.39, color='#000000', ease=vb.ease_in_out_quart):
    """Draw letterbox bars over whatever is already on `cv`. At `p` = 0 there
    are no bars; at `p` = 1 the bars leave a centred band `ratio` (width over
    height, e.g. 2.39 or 1.85) wide. Returns the visible band as a `vb.Box`.

    Call it after drawing the shot, with a fixed `p=1` for a whole scene or a
    rising `p` to bring the bars in (falling to take them away)."""
    W, H = cv.width, cv.height
    full = max(0.0, (H - W / ratio) / 2)  # each bar's height once fully in
    bar = full * ease(vb.clamp01(p))
    if bar > 0:
        cv.rect(0, 0, W, bar, color)
        cv.rect(0, H - bar, W, bar, color)
    return vb.Box(0, bar, W, H - 2 * bar)


def draw(n, cv):
    img = demo.photo()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))
    letterbox(cv, demo.phase(n, 0.6, 1.8))
    if n / demo.FPS > 1.9:
        f = demo.mono(26)
        w, h = vb.text.block_size(['2.39 : 1'], f)
        vb.text.draw(cv, ['2.39 : 1'], f, demo.W - w - 40, demo.H - h - 34, demo.MUTED)


TECHNIQUE = Technique(
    id='letterbox',
    name='Letterbox',
    family='vfx',
    group='Editing & frame',
    aliases=('cinemascope bars', 'widescreen bars', 'matte bars', 'cinematic bars'),
    definition='Black bands slide in over the top and bottom of the shot so the picture that remains '
               'looks like a wide cinema frame.',
    phrasings=('add black bars above and below to make it look like a movie',
               'crop the shot to a widescreen 2.39 look with bars',
               'bring in cinematic bars at the top and bottom'),
    related=('box-wipe', 'copper-bars', 'video-clipped-inside-letterforms', 'vhs-tracking-bar', 'corner-wipe',
             'film-edge-frame'),
    api=('videobuilder.techniques.vfx.letterbox.letterbox',),
    demo=lambda: demo.film(draw),
)
