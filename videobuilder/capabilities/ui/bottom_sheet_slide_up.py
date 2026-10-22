"""Bottom Sheet Slide-up: a panel rises from the bottom edge over a dimmed
screen, and is pulled back down by its handle to dismiss it."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

SHEET = '#24262e'
ROW = '#2e3039'


def bottom_sheet(cv, p, content=None, height=None, width=None, color=SHEET, scrim=0.5, radius=32,
                 grabber=True):
    """Draw a bottom sheet `p` of the way up (0 hidden below the frame, 1
    fully raised) over whatever is already on `cv`, and return its Box.

    The screen behind dims to `scrim` black in step with `p`. The sheet is
    `height` tall (default 55% of the frame) and `width` wide (default the
    full frame), centred, rounded on top, with a grab handle unless
    `grabber=False`. `content(cv, box)` draws inside it, clipped, in sheet
    coordinates that ride along with it. `p` is used as given: ease it in
    the caller, e.g. `ease_out_quint` to raise and `ease_in_out_quart` to
    drag it back down."""
    W, H = cv.width, cv.height
    height = height or H * 0.55
    width = width or W
    p = vb.clamp01(p)
    if scrim and p > 0:
        cv.fill('#000000', alpha=scrim * p)
    if p <= 0:
        return vb.Box((W - width) / 2, H, width, height)
    x, y = (W - width) / 2, H - height * p
    # Run the panel past the bottom edge so only its top corners are rounded.
    cv.shadow(x, y, width, height + radius, radius=radius, dy=-6, blur=40, color=(0, 0, 0, 0.5))
    cv.rect(x, y, width, height + radius, color, radius=radius)
    if grabber:
        cv.rect(W / 2 - 36, y + 16, 72, 8, demo.MUTED, radius=4, alpha=0.8)
    box = vb.Box(x, y, width, height)
    if content:
        with cv.clip(x, y, width, height + radius, radius=radius):
            content(cv, box)
    return box


def _screen(cv):
    """The app behind the sheet: a card with a title, two lines and a button."""
    x, y, w, h = demo.W / 2 - 340, 150, 680, 300
    cv.shadow(x, y, w, h, radius=24, dy=10, blur=30, color=(0, 0, 0, 0.4))
    cv.rect(x, y, w, h, demo.LINE, radius=24)
    for i, (bw, a) in enumerate(((420, 0.9), (340, 0.55), (240, 0.55))):
        cv.rect(x + 48, y + 52 + i * 36, bw, 14 if i == 0 else 12, demo.INK, radius=6, alpha=a)
    cv.rect(x + 48, y + h - 96, 150, 52, demo.TEAL, radius=12)
    demo.dot(cv, x + w - 80, y + h - 70, 30, color=demo.ACCENT)
    cv.rect(x + w - 94, y + h - 73, 28, 6, demo.INK, radius=3)
    cv.rect(x + w - 83, y + h - 84, 6, 28, demo.INK, radius=3)


def _content(cv, box):
    x, y = box.x + 90, box.y + 64
    cv.rect(x, y, 460, 16, demo.INK, radius=8, alpha=0.9)
    cv.rect(x, y + 34, 320, 12, demo.MUTED, radius=6)
    for i, c in enumerate((demo.TEAL, demo.ACCENT, '#e8b84a')):
        ry = y + 84 + i * 96
        cv.rect(x - 20, ry, box.w - 140, 78, ROW, radius=16)
        demo.dot(cv, x + 24, ry + 39, 18, color=c)
        cv.rect(x + 66, ry + 33, 360 - 70 * i, 12, demo.INK, radius=6, alpha=0.7)


def draw(n, cv):
    up = vb.ease_out_quint(demo.phase(n, 0.35, 1.05))
    down = vb.ease_in_out_quart(demo.phase(n, 1.9, 2.55))
    p = up * (1 - down)
    _screen(cv)
    tap = demo.phase(n, 0.1, 0.45)  # a tap on the + button calls the sheet up
    if 0 < tap < 1:
        demo.dot(cv, demo.W / 2 + 260, 380, 30 + 30 * tap, color=demo.INK, alpha=0.4 * (1 - tap))
    box = bottom_sheet(cv, p, _content, height=demo.H * 0.58, width=demo.W - 240)
    # A fingertip on the handle while the sheet is dragged back down.
    touch = demo.phase(n, 1.6, 1.8) * (1 - demo.phase(n, 2.55, 2.75))
    if touch > 0 and box.y < demo.H:
        demo.dot(cv, demo.W / 2, box.y + 20, 26, color=demo.INK, alpha=0.35 * touch)
    if p > 0:
        cv.mark('sheet', box.x, box.y, box.w, min(box.h, demo.H - box.y))


TECHNIQUE = Technique(
    id='bottom-sheet-slide-up',
    name='Bottom sheet slide-up',
    family='ui',
    group='Overlays & menus',
    aliases=('bottom sheet', 'modal sheet', 'sheet drawer', 'drawer reveal', 'modal slide-up'),
    definition='A panel of options rises from the bottom edge of the screen while the view behind it dims, '
               'and is pulled back down by its handle to close.',
    phrasings=('pop up a menu from the bottom of the phone screen',
               'a drawer that slides up over the app and swipes down to close',
               'show the options in a sheet coming up from below'),
    related=('tab-panel-slide', 'tab-underline-slide', 'uncover', 'shutter-wipe', 'slide-over-cover',
             'paper-fold-reveal'),
    api=('videobuilder.techniques.ui.bottom_sheet_slide_up.bottom_sheet',),
    demo=lambda: demo.film(draw),
)
