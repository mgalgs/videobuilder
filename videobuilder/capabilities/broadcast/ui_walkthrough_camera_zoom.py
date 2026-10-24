"""UI walkthrough camera zoom: the same idea as Camera on a screenshot
(`../camera/camera_on_a_screenshot.py`), which keeps the capability through
Canvas.view-style framing: a whole app screen is shown, then the camera
pushes in and pans so one region of the interface fills the frame. This
module's own code stays (a film may still import it), but it is no longer
a capability of its own."""
import videobuilder as vb

from .. import _demo as demo

MERGED_INTO = 'camera-on-a-screenshot'


def ui_camera_zoom(cv, screen, focus, p, margin=0.08, max_zoom=4.0):
    """Draw `screen(cv)` -- a UI laid out over the whole frame -- through a
    camera at progress `p` (0 -> 1): at 0 the full screen, at 1 the region
    `focus` = (x, y, w, h), in frame px, centred and as large as fits inside
    `margin` (a fraction of the frame) on every side. The zoom runs evenly in
    log space while the region's centre glides to the frame's centre; pass an
    eased `p`. Returns the focus region's on-screen (x, y, w, h).

    Zoom back out by running `p` from 1 to 0; walk between two regions by
    zooming out of one and into the next."""
    W, H = cv.width, cv.height
    fx, fy, fw, fh = focus
    target = min(W * (1 - 2 * margin) / fw, H * (1 - 2 * margin) / fh)
    z = vb.log_lerp(1.0, max(1.0, min(max_zoom, target)), vb.clamp01(p))
    q = vb.clamp01(p)
    fcx, fcy = fx + fw / 2, fy + fh / 2
    sx, sy = fcx + (W / 2 - fcx) * q, fcy + (H / 2 - fcy) * q   # where the region's centre sits now
    dx, dy = sx - fcx * z, sy - fcy * z
    with cv.layer(dx=dx, dy=dy, scale=z):
        screen(cv)
    return dx + fx * z, dy + fy * z, fw * z, fh * z


# ---- the demo: a plain photo-editor screen, zooming onto its adjust panel ----

U = demo.W / 1920   # the screen is laid out on a 1920 x 1080 grid, then scaled to the frame
APP = vb.Box(150, 90, 1620, 900)
PANEL = vb.Box(APP.right - 360, APP.y + 76, 330, 520)
SLIDERS = (('Exposure', 0.55), ('Contrast', 0.35), ('Warmth', 0.7))
# The final framing: 16:9, so the region fills the frame edge to edge. The panel sits against the window's
# right edge, so the view stops just inside it and reaches left over the canvas rather than past the window;
# its top clears the title bar, so the Export button leaves the frame whole instead of being cut.
VIEW = vb.Box(APP.right - 4 - 800, PANEL.y + 82, 800, 450)


def app_screen(cv):
    """A product screen: window, top bar, tool rail, canvas, thumbnails, and
    an adjust panel with three sliders."""
    with cv.layer(scale=U):
        _app(cv)


def _app(cv):
    a, line = APP, demo.LINE
    cv.shadow(*a, radius=22, dy=18, blur=50, color=(0, 0, 0, 0.55))
    cv.rect(*a, '#1b1d23', radius=22)
    cv.outline(*a, line, width=2, radius=22)
    cv.line(a.x, a.y + 64, a.right, a.y + 64, line, width=2)
    vb.text.draw(cv, ['Studio'], demo.font(26, 800), a.x + 100, a.y + 18, demo.INK)
    vb.text.draw(cv, ['Untitled / 03'], demo.font(20, 500), a.x + 520, a.y + 21, demo.MUTED)
    cv.rect(a.right - 130, a.y + 16, 100, 34, demo.TEAL, radius=10)
    vb.text.draw(cv, ['Export'], demo.font(18, 700), a.right - 112, a.y + 22, demo.BG)
    cv.line(a.x + 80, a.y + 64, a.x + 80, a.bottom, line, width=2)
    for i in range(5):
        cv.outline(a.x + 26, a.y + 100 + i * 64, 28, 28, demo.MUTED, width=2, radius=7,
                   alpha=1.0 if i == 1 else 0.5)
    art = vb.Box(a.x + 112, a.y + 96, PANEL.x - a.x - 140, 470)
    with cv.clip(*art, 14):
        cv.fill('#3f5a8c')
        cv.rect(art.x, art.y + art.h * 0.62, art.w, art.h, '#2a3a5c')
        demo.dot(cv, art.x + art.w * 0.7, art.y + art.h * 0.3, r=48, color='#f2b632')
    for i in range(4):
        tw = (art.w - 3 * 18) / 4
        tx = art.x + i * (tw + 18)
        cv.rect(tx, art.bottom + 28, tw, 110, '#2d3442', radius=10)
        if i == 0:
            cv.outline(tx - 3, art.bottom + 25, tw + 6, 116, '#f2b632', width=3, radius=12)
    cv.line(PANEL.x - 14, a.y + 64, PANEL.x - 14, a.bottom, line, width=2)
    vb.text.draw(cv, ['Adjust'], demo.font(26, 800), PANEL.x + 14, PANEL.y + 22, demo.INK)
    for i, (label, v) in enumerate(SLIDERS):
        y = PANEL.y + 110 + i * 120
        vb.text.draw(cv, [label], demo.font(20, 600), PANEL.x + 14, y, demo.MUTED)
        vb.text.draw(cv, [f'{round((v - 0.5) * 200):+d}'], demo.font(20, 600), PANEL.right - 60, y, demo.INK)
        x0, x1, ty = PANEL.x + 14, PANEL.right - 24, y + 52
        cv.line(x0, ty, x1, ty, line, width=6)
        cv.line(x0, ty, x0 + (x1 - x0) * v, ty, demo.ACCENT, width=6)
        demo.dot(cv, x0 + (x1 - x0) * v, ty, r=11, color=demo.INK)
    cv.rect(PANEL.x + 14, PANEL.bottom - 70, PANEL.w - 38, 48, '#2a2d36', radius=10)
    vb.text.draw(cv, ['Reset'], demo.font(18, 700), PANEL.x + PANEL.w / 2 - 34, PANEL.bottom - 58, demo.INK)


def draw(n, cv):
    p = vb.ease_in_out_quart(demo.phase(n, 0.6, 2.0))
    ui_camera_zoom(cv, app_screen, tuple(v * U for v in VIEW), p, margin=0)
