"""Video Clipped Inside Letterforms: moving footage shows only through the
letter shapes of a word, so the type is a window onto the picture behind it."""
import math
from contextlib import contextmanager

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def text_outline(cv, line, font, x, y):
    """Set `line`'s glyph outlines as the current cairo path, placed as
    `text.draw` would place it with its top-left at (x, y). Returns the Box of
    the ink (the letters themselves, not the line box)."""
    from gi.repository import PangoCairo
    ctx = cv.ctx
    content, _ = vb.text._content(font)
    ctx.new_path()
    ctx.move_to(x, y + (vb.text.line_height(font) - content) / 2)
    PangoCairo.layout_path(ctx, vb.text._layout(ctx, line, font))
    x0, y0, x1, y1 = ctx.path_extents()
    return vb.Box(x0, y0, x1 - x0, y1 - y0)


@contextmanager
def inside_letters(cv, line, font, x, y):
    """A block whose drawing shows only inside `line`'s letters, top-left at
    (x, y). Yields the Box of the ink, so the body can fit its footage to the
    word: `with inside_letters(cv, 'SUNSET', f, x, y) as ink: cv.image(...)`."""
    ctx = cv.ctx
    ctx.save()
    ink = text_outline(cv, line, font, x, y)
    ctx.clip()
    try:
        yield ink
    finally:
        ctx.restore()


def video_in_text(cv, line, font, x, y, paint):
    """Draw `line` filled with footage: `paint(cv, ink)` draws the current
    frame of the moving picture (a video frame, a panning photo, a
    procedural scene) and only what lands inside the letters shows. `ink`
    is the Box of the letters. Returns that Box."""
    with inside_letters(cv, line, font, x, y) as ink:
        paint(cv, ink)
    return ink


WORD = 'SUNSET'


def _footage(n):
    """The demo's 'video': a sunset photo panning sideways, slowly pushing in,
    with a sun drifting down and light bands sweeping across it."""
    t = n / demo.FPS

    def paint(cv, ink):
        img = demo.photo()
        k = 1.25 + 0.06 * t / demo.SECONDS                      # slow push-in
        w, h = ink.w * k, ink.w * k * img.h / img.w
        h = max(h, ink.h * k)
        w = h * img.w / img.h
        pan = (w - ink.w) * (0.15 + 0.7 * t / demo.SECONDS)      # sideways pan
        cv.image(img, ink.x - pan, ink.y + (ink.h - h) / 2, w, h)
        sx = ink.x + ink.w * (0.75 - 0.25 * t / demo.SECONDS)
        sy = ink.y + ink.h * (0.25 + 0.35 * t / demo.SECONDS)
        demo.dot(cv, sx, sy, r=ink.h * 0.16, color='#ffcf7a', alpha=0.9)
        for i in range(3):                                      # sweeping light bands
            bx = ink.x + ((t * 520 + i * 610) % (ink.w + 600)) - 300
            cv.ctx.save()
            cv.ctx.translate(bx, ink.y + ink.h / 2)
            cv.ctx.rotate(math.radians(18))
            cv.rect(-40, -ink.h, 80 - 25 * i, ink.h * 2, '#ffffff', alpha=0.16)
            cv.ctx.restore()
    return paint


def draw(n, cv):
    f = demo.font(220, 900)
    w, h = vb.text.block_size([WORD], f)
    x, y = (demo.W - w) / 2, (demo.H - h) / 2
    ink = video_in_text(cv, WORD, f, x, y, _footage(n))
    cv.mark('text', *ink)


CAPABILITY = Capability(
    id='video-clipped-inside-letterforms',
    name='Video clipped inside letterforms',
    family='typography',
    group='Masking and clipping',
    aliases=('video text fill', 'text as video mask', 'footage in type', 'knockout type'),
    definition='Big bold letters act as cut-out windows, and a moving picture plays through '
               'them while everything outside the letters stays plain background.',
    phrasings=('play the video inside the letters of the title',
               'fill the text with moving footage',
               'make the word a window you can see the clip through'),
    related=('text-mask-reveal', 'pixel-sort-text', 'character-blur-in', 'wipe-reveal',
             'character-rise', 'letterbox'),
    api=('videobuilder.capabilities.typography.video_clipped_inside_letterforms.video_in_text',
         'videobuilder.capabilities.typography.video_clipped_inside_letterforms.inside_letters',
         'videobuilder.capabilities.typography.video_clipped_inside_letterforms.text_outline'),
    demo=lambda: demo.film(draw),
)
