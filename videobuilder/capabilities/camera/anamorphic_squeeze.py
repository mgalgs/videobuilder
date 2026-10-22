"""Anamorphic squeeze: a picture shot through an anamorphic lens is recorded
squashed sideways, so round things look tall and thin; desqueezing stretches
it back out to a wide letterboxed frame, with the lens's long horizontal
flare streaks across the highlights."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ...ease import ease_in_out_quart


def anamorphic_squeeze(cv, draw, p, squeeze=2.0, center=(demo.W / 2, demo.H / 2)):
    """Draw `draw(cv)` squeezed sideways about `center` at progress `p`:
    at 0 it is `1 / squeeze` of its width (the raw, squashed recording), at 1
    it is desqueezed back to its true width. Only x is scaled, so circles go
    from tall ovals to round. Run `p` the other way to squeeze a shot down.

    In a film: `anamorphic_squeeze(cv, shot, ease_in_out_quart(shot.f / frames))`."""
    sx = 1 / squeeze + (1 - 1 / squeeze) * p
    cx, cy = center
    c = cv.ctx
    c.save()
    c.translate(cx * (1 - sx), 0)
    c.scale(sx, 1)
    try:
        draw(cv)
    finally:
        c.restore()


def anamorphic_streak(cv, x, y, length, color='#6fb6ff', alpha=1.0, thickness=6):
    """A horizontal anamorphic lens flare through the highlight (x, y): a thin
    bright core inside wider, fainter glows, `length` px end to end, tapering
    out toward both ends."""
    if alpha <= 0 or length <= 0:
        return
    for k, (w, a) in enumerate(((thickness * 9, 0.08), (thickness * 4, 0.18), (thickness * 1.6, 0.45),
                                (thickness * 0.5, 0.9))):
        span = length * (1 - 0.18 * k)
        for i in range(12):  # stepped taper: each slice shorter and brighter toward the core
            f = i / 12
            half = span / 2 * (1 - f)
            cv.rect(x - half, y - w / 2, 2 * half, w, '#ffffff' if k == 3 else color,
                    radius=w / 2, alpha=alpha * a / 4)
    demo.dot(cv, x, y, thickness * 2.2, color='#ffffff', alpha=alpha)


def letterbox(cv, aspect=2.39, color='#000000', alpha=1.0):
    """Black bars top and bottom framing a `aspect`:1 picture in the middle;
    returns the picture's (x, y, w, h)."""
    h = cv.width / aspect
    bar = max(0.0, (cv.height - h) / 2)
    if bar and alpha > 0:
        cv.rect(0, 0, cv.width, bar, color, alpha=alpha)
        cv.rect(0, cv.height - bar, cv.width, bar, color, alpha=alpha)
    return 0, bar, cv.width, cv.height - 2 * bar


# ---- demo: a night street of round lights, desqueezed from 2x ----
_ASPECT = 2.39
_PIC_H = demo.W / _ASPECT
_TOP = (demo.H - _PIC_H) / 2
_LIGHTS = ((300, 0.30, 70, demo.ACCENT), (640, 0.62, 95, demo.TEAL),
           (1300, 0.58, 110, demo.ACCENT), (1600, 0.33, 80, demo.TEAL))
_SUN = (demo.W * 0.5, _TOP + _PIC_H * 0.42)


def _scene(cv):
    img = demo.photo()
    with cv.clip(0, _TOP, demo.W, _PIC_H):
        cv.image(img, *vb.Box(0, _TOP, demo.W, _PIC_H).cover(img.w, img.h))
        cv.rect(0, _TOP, demo.W, _PIC_H, '#000000', alpha=0.45)
        for x, fy, r, col in _LIGHTS:
            demo.dot(cv, x, _TOP + _PIC_H * fy, r, color=col, alpha=0.55)
            demo.dot(cv, x, _TOP + _PIC_H * fy, r * 0.55, color=col, alpha=0.6)
        demo.dot(cv, *_SUN, 46, color='#ffffff')
        cv.outline(0, _TOP, demo.W, _PIC_H, demo.INK, width=4, alpha=0.4)


def _draw(n, cv):
    p = ease_in_out_quart(demo.phase(n, 0.6, 2.0))
    anamorphic_squeeze(cv, _scene, p)
    letterbox(cv, _ASPECT, color=demo.BG)
    flare = demo.phase(n, 1.8, 2.5)
    anamorphic_streak(cv, *_SUN, length=demo.W * 1.1 * flare, alpha=flare)
    label = f'{2 / (1 + p):.1f}x  SQUEEZED' if p < 1 else '2.39 : 1  DESQUEEZED'
    demo.word(cv, label, demo.W / 2, _TOP / 2, size=40, color=demo.MUTED, font=demo.mono(40))
    cv.mark('picture', demo.W / 2 * (1 - (0.5 + 0.5 * p)), _TOP, demo.W * (0.5 + 0.5 * p), _PIC_H)


TECHNIQUE = Technique(
    id='anamorphic-squeeze',
    name='Anamorphic squeeze',
    family='camera',
    group='Lens',
    aliases=('anamorphic desqueeze', 'anamorphic lens look', 'anamorphic widescreen', 'anamorphic flare'),
    definition='A picture squashed narrow, so round lights look like tall ovals, stretches out sideways '
               'into a wide letterboxed frame, often with long thin blue flares through the bright spots.',
    phrasings=('make it look like it was shot on an anamorphic lens',
               'stretch the squished footage back out to cinema widescreen',
               'that movie look with the black bars and long blue lens streaks'),
    related=('zoom-to-detail-magnifier', 'scale-zoom-through', 'infinite-zoom-tunnel', 'optical-zoom',
             'dolly-zoom', 'crt-curvature'),
    api=('videobuilder.techniques.camera.anamorphic_squeeze.anamorphic_squeeze',
         'videobuilder.techniques.camera.anamorphic_squeeze.anamorphic_streak',
         'videobuilder.techniques.camera.anamorphic_squeeze.letterbox'),
    demo=lambda: demo.film(_draw),
)
