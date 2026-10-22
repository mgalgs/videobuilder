"""Image Hover Zoom: a pointer moves onto a picture card and the picture
grows inside its frame, the frame itself staying put and cropping it; when
the pointer leaves, the picture eases back. Built on `Canvas.view`, which
already shows an image through a clipped window at any scale."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

POINTER = ((0, 0), (0, 27), (7, 21), (12, 32), (17.5, 29.5), (12.5, 19), (21, 19))


def hover_zoom(cv, img, box, p, zoom=1.25, focus=None, radius=18, ease=vb.ease_in_out_quart):
    """Draw `img` covering `box`, zoomed in by up to `zoom` as the hover
    progress `p` runs 0 -> 1 (run it back 1 -> 0 for the un-hover). The
    image grows toward `focus` (image px; default its centre), which is
    held back from the edges so the picture always fills `box`; it stays
    clipped to `box` with corner `radius`. Returns the `View`."""
    box = vb.Box(*box)
    s = max(box.w / img.w, box.h / img.h) * (1 + (zoom - 1) * ease(vb.clamp01(p)))
    fx, fy = focus if focus is not None else (img.w / 2, img.h / 2)
    hw, hh = box.w / s / 2, box.h / s / 2
    center = min(max(fx, hw), img.w - hw), min(max(fy, hh), img.h - hh)
    return cv.view(img, box, center=center, scale=s, radius=radius)


def pointer(cv, x, y, size=1.0, color=demo.INK, edge=demo.BG):
    """An arrow mouse pointer with its tip at (x, y)."""
    pts = [(x + px * size, y + py * size) for px, py in POINTER]
    cv.shape_shadow(pts, dx=2, dy=4, blur=6, color=(0, 0, 0, 0.45))
    c = cv.ctx
    c.new_path()
    c.move_to(*pts[0])
    for pt in pts[1:]:
        c.line_to(*pt)
    c.close_path()
    c.set_source_rgba(*vb.rgba(color))
    c.fill_preserve()
    c.set_source_rgba(*vb.rgba(edge))
    c.set_line_width(2)
    c.stroke()


def draw(n, cv):
    img = demo.photo()
    w, h, gap = 250, 180, 30
    x0, y = (demo.W - 3 * w - 2 * gap) / 2, (demo.H - h) / 2
    hover = demo.phase(n, 0.9, 1.5) - demo.phase(n, 2.2, 2.8)
    for i in range(3):
        box = vb.Box(x0 + i * (w + gap), y, w, h)
        p = hover if i == 1 else 0
        cv.shadow(*box, radius=12, dy=6, blur=18, color=(0, 0, 0, 0.45))
        hover_zoom(cv, img, box, p, zoom=1.35, focus=(img.w * 0.75, img.h * 0.3), radius=12)  # toward the sun
        cv.outline(*box, demo.ACCENT, width=3, radius=12, alpha=vb.ease_in_out_quart(p))
        cv.mark(f'image{i}', *box)
    # The pointer glides onto the middle card, rests, then slides away.
    tx, ty = demo.W / 2 + 20, demo.H / 2 + 10
    come = vb.ease_out_quint(demo.phase(n, 0.2, 0.95))
    go = vb.ease_in_out_quart(demo.phase(n, 2.1, 2.8))
    pointer(cv, tx + (demo.W * 0.32) * (1 - come) + 90 * go, ty + 130 * (1 - come) + 115 * go)


CAPABILITY = Capability(
    id='image-hover-zoom',
    name='Image hover zoom',
    family='ui',
    group='Cursor & hover',
    aliases=('hover zoom', 'zoom on hover', 'image scale on hover', 'thumbnail hover zoom'),
    definition='When a pointer rests on a picture, the picture slowly enlarges inside its fixed frame, '
               'which crops the edges, and shrinks back once the pointer moves off.',
    phrasings=('the photo grows a little inside its card when the mouse goes over it',
               'mouse over a thumbnail and the image pushes in without the box getting bigger',
               'a gallery tile whose picture zooms in on hover'),
    related=('zoom-to-detail-magnifier', 'scale-zoom-through', 'zoom-blur', 'ui-walkthrough-camera-zoom',
             'infinite-zoom-tunnel', 'nearest-neighbor-upscale'),
    api=('videobuilder.capabilities.ui.image_hover_zoom.hover_zoom',
         'videobuilder.Canvas.view',
         'videobuilder.capabilities.ui.image_hover_zoom.pointer'),
    demo=lambda: demo.film(draw),
)
