"""Pop-art filter: the picture posterized to a loud flat palette, each flat
area screened with drifting Ben-Day dots in a deeper shade of itself
(bigger in the shadows, small in the highlights), and thick dark outlines
on every strong edge. The dots drift on `t`, so even a still screenshot
crawls with them."""
from PIL import Image, ImageEnhance

from . import Filter, edges, grow, halftone, luma, palette_image, posterize, recolour, shrink, work_factor

INK = '#141018'
# each fill, and the colour its dots print in
FILLS = ('#fff6e4', '#ffe23a', '#ff9a2a', '#e8202a', '#ff4f9a', '#33c6e8', '#2a4ad8', '#4ab84a', INK)
DOTS = ('#f6a8c0', '#f2a020', '#d8601a', '#a8101a', '#c81f6a', '#1f8fc8', '#1a2a9a', '#1e7a2a', INK)
_PALETTE = palette_image(FILLS)


def treat(im, t, age, u):
    k = work_factor(u)
    small = shrink(im, k)
    loud = ImageEnhance.Contrast(ImageEnhance.Color(small).enhance(1.9)).enhance(1.25)
    q = posterize(loud, _PALETTE)
    fill, dots = grow(q.convert('RGB'), im.size), grow(recolour(q, DOTS), im.size)
    # a halftone in the area's own deeper shade: every area gets dots, the shadows the biggest
    tone = grow(luma(small).point(lambda v: int(70 + 0.65 * (255 - v))), im.size, Image.BILINEAR)
    mask = halftone(tone, 16 * u, dx=36 * u * t, dy=22 * u * t)
    out = Image.composite(dots, fill, mask)
    ink = grow(edges(luma(small), level=34, blur=0.8, thick=4.5 * u / k), im.size)
    out.paste(INK, (0, 0, *im.size), ink)
    return out


FILTER = Filter('pop-art', 'Pop-art filter', 'loud flat colour, drifting dots, thick outlines', treat,
                aliases=('comic-book halftone',))
