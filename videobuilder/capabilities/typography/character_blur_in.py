"""Character blur-in: each letter arrives as a faint smear and pulls into
sharp focus, the letters starting one after another from left to right."""
import videobuilder as vb
from videobuilder.type import kit as type_kit

from .. import _demo as demo
from ..schema import Capability


def blur_in(text, p, overlap=2.5, ease=vb.ease_out_quint):
    """Each character of `text` at progress `p` (0 -> 1) as its own focus,
    0 (fully blurred, faint) to 1 (sharp). Characters start in order, each
    taking `overlap` characters' worth of stagger to settle, so several are
    mid-pull at once; the first starts at 0 and the last lands at 1."""
    n = len(text)
    span = 1.0 / (1 + (n - 1) / overlap) if n > 1 else 1.0
    step = (1 - span) / (n - 1) if n > 1 else 0.0
    return [ease(vb.clamp01((p - i * step) / span)) for i in range(n)]


def draw_blur_in(cv, text, font, x, y, p, color, blur=None, alpha_from=0.0, **kw):
    """Draw `text` from its top-left (x, y) at progress `p`, each letter
    blurred by up to `blur` px (default a third of the font size) and faded
    from `alpha_from`, sharpening in turn (`kw` goes to `blur_in`). Letters
    sit at their final places throughout, so the line never shifts.
    Returns the Box of the finished line."""
    blur = font.size / 3 if blur is None else blur
    xs, width = type_kit.advances(text, font)
    lh = vb.text.line_height(font)
    for ch, cx, f in zip(text, xs, blur_in(text, p, **kw)):
        if ch.isspace() or alpha_from + f <= 0:
            continue
        gx = x + cx
        type_kit.blurred(cv, vb.Box(gx, y, vb.text.measure(ch, font), lh), blur * (1 - f),
                         lambda c, ch=ch, gx=gx: vb.text.draw(c, [ch], font, gx, y, color),
                         alpha=alpha_from + (1 - alpha_from) * f)
    return vb.Box(x, y, width, lh)


def draw(n, cv):
    f = demo.font(150, 800)
    text = 'MOTION'
    w, h = vb.text.block_size([text], f)
    box = draw_blur_in(cv, text, f, (demo.W - w) / 2, (demo.H - h) / 2, demo.phase(n, 0.3, 2.3),
                       demo.INK, alpha_from=0.15)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='character-blur-in',
    name='Character blur-in',
    family='typography',
    group='Per-unit reveals',
    aliases=('focus-in text', 'defocus reveal', 'letter blur reveal'),
    definition='A word appears as soft, faint smudges that sharpen into crisp letters one at a time, '
               'the focus travelling along the line.',
    phrasings=('make each letter of the title go from blurry to sharp, one after another',
               'the text comes into focus character by character',
               'letters fade in out of a blur in sequence'),
    related=('text-mask-reveal', 'typewriter-reveal', 'blur-dissolve', 'focus-ring-draw', 'focus-blur-out',
             'outline-pulse-glow'),
    api=('videobuilder.capabilities.typography.character_blur_in.draw_blur_in',
         'videobuilder.capabilities.typography.character_blur_in.blur_in',
         'videobuilder.type.kit.blurred'),
    demo=lambda: demo.film(draw),
)
