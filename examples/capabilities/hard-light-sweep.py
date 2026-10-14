"""Capability: hard-light sweep. A dim, shadowed version of a generated
product scene sits underneath a warm, lit version clipped to a hard-edged
band -- a slanted shaft of light with window-mullion bars cut out of it --
that sweeps across the frame, as if sunlight were moving across a desk.

    python -m videobuilder preview examples/capabilities/hard-light-sweep.py

LOOP = True: the band's position is one continuous wrapping phase
(`n % PERIOD / PERIOD`), so frame 0 and the frame just past the last are the
same point in the cycle by construction -- no enter/exit needed.
"""
import sys
from pathlib import Path

import cairo
from PIL import Image as PILImage, ImageDraw, ImageEnhance, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import Box, text  # noqa: E402

LOOP = True
FPS = 30
PERIOD = 100   # ~3.3 s true period

SCENE_W, SCENE_H = 600, 420
PAGE_BG = '#eef0f2'
CARD_BG = '#ffffff'
CARD_BORDER = '#d7dbe2'
TEXT_DARK = '#242731'
TEXT_MUTED = '#878d99'


def _font(size):
    return ImageFont.truetype(str(_kit.ASSETS / 'Inter-Variable.ttf'), size)


def _build_scene():
    """A small generated "desk" scene: a card with a headline, a short bar
    group and a button -- enough surface area and a few hard edges for the
    light band to read against."""
    img = PILImage.new('RGB', (SCENE_W, SCENE_H), PAGE_BG)
    d = ImageDraw.Draw(img)
    card = (40, 40, SCENE_W - 40, SCENE_H - 40)
    d.rounded_rectangle(card, radius=20, fill=CARD_BG, outline=CARD_BORDER, width=2)
    d.text((76, 76), 'Q3 performance', font=_font(30), fill=TEXT_DARK)
    d.text((76, 118), 'Up across every region', font=_font(20), fill=TEXT_MUTED)
    base_x, base_y, bar_w, gap = 76, 300, 44, 26
    for i, h in enumerate((60, 95, 70, 130, 110)):
        x = base_x + i * (bar_w + gap)
        color = _kit.ACCENT if i == 3 else _kit.TEAL
        d.rounded_rectangle((x, base_y - h, x + bar_w, base_y), radius=8, fill=color)
    d.rounded_rectangle((76, base_y + 40, 216, base_y + 84), radius=10, fill=TEXT_DARK)
    d.text((104, base_y + 54), 'Export', font=_font(20), fill=PAGE_BG)
    return img


def _tinted(img, color, amount):
    overlay = PILImage.new('RGB', img.size, color)
    return PILImage.blend(img, overlay, amount)


_SCENE = _build_scene()
DIM = vb.Image.from_pil(_tinted(ImageEnhance.Brightness(ImageEnhance.Color(_SCENE).enhance(0.4)).enhance(0.3),
                                (8, 12, 26), 0.5))
LIT = vb.Image.from_pil(_tinted(ImageEnhance.Brightness(ImageEnhance.Contrast(_SCENE).enhance(1.08)).enhance(1.22),
                                (255, 195, 120), 0.22))

TITLE_F = _kit.font(32, 700)

BAND_W = 170
SKEW = 90
N_BARS = 3
BAR_W = 16
BAR_GAP = (BAND_W - N_BARS * BAR_W) / (N_BARS + 1)


def light_clip(ctx, x, w, h, skew):
    """Clip to a slanted band from `x` to `x + w`, skewed `skew` px top to
    bottom, with evenly spaced vertical mullion bars cut out of it (an
    even-odd fill rule: the band's own path plus each bar's path, wound the
    same way, cancels out where they overlap)."""
    ctx.new_path()
    ctx.move_to(x, 0)
    ctx.line_to(x + w, 0)
    ctx.line_to(x + w + skew, h)
    ctx.line_to(x + skew, h)
    ctx.close_path()
    for i in range(N_BARS):
        bx = x + BAR_GAP * (i + 1) + BAR_W * i
        ctx.move_to(bx, 0)
        ctx.line_to(bx + BAR_W, 0)
        ctx.line_to(bx + BAR_W + skew, h)
        ctx.line_to(bx + skew, h)
        ctx.close_path()
    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    ctx.clip()


def draw(n, cv):
    cv.fill(_kit.BG)
    s = _kit.safe(cv, 64)
    _kit.text_marked(cv, 'title', text.wrap('Hard-light sweep', TITLE_F, s.w), TITLE_F, s.x, s.y, _kit.INK)

    box = Box(s.x, s.y + 92, s.w, s.w * SCENE_H / SCENE_W)
    with cv.clip(*box, radius=16):
        cv.image(DIM, *box)
        phase = (n % PERIOD) / PERIOD
        band_x = box.x - BAND_W - SKEW + phase * (box.w + BAND_W + SKEW)
        ctx = cv.ctx
        ctx.save()
        ctx.translate(0, box.y)   # light_clip's y runs 0..h; the scene box sits at box.y
        light_clip(ctx, band_x, BAND_W, box.h, SKEW)
        ctx.translate(0, -box.y)
        cv.image(LIT, *box)
        ctx.restore()
    cv.outline(*box, _kit.LINE, width=2, radius=16)
    cv.mark('scene', *box)

    _kit.label(cv, 'caption', 'A desk scene, dim and lit layers', s.x, box.bottom + 20, align='left')


FILM = vb.Film(draw=draw, fps=FPS, frames=PERIOD, formats=(_kit.FORMAT,), background=_kit.BG,
               keyframes=(0, PERIOD // 3, 2 * PERIOD // 3))

if __name__ == '__main__':
    vb.main(__file__)
