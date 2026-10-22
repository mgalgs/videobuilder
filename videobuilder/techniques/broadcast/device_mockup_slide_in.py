"""Device mockup slide-in: a drawn laptop or phone, its screen showing the
product, glides in from off frame with a slight tilt and settles into place,
so a UI walkthrough opens on the device rather than on a bare screenshot."""
import math

import videobuilder as vb
from videobuilder import Box

from .. import _demo as demo
from ..schema import Technique
from ...compendium.components import _images_util as u

BODY = '#0e0f13'
RIM = '#3a3d47'
METAL = '#c9ccd3'
METAL_DARK = '#9a9ea8'


def _screen(cv, screen, box, radius=0):
    """Fill `box` with `screen`: a `vb.Image` cover-fitted from the top, or a
    callable `screen(cv, box)` drawn clipped to the box."""
    if callable(screen):
        with cv.clip(*box, radius):
            screen(cv, box)
    else:
        u.cover_image(cv, screen, box, fy=0.0, radius=radius)


def phone_frame(cv, x, y, w, h, screen):
    """A plain, unbranded phone filling (x, y, w, h), its screen showing
    `screen` (an image or a `screen(cv, box)` callable). Returns the screen Box."""
    b = w * 0.045
    r = w * 0.15
    cv.shadow(x, y, w, h, radius=r, dy=h * 0.04, blur=h * 0.08, color=(0, 0, 0, 0.55))
    cv.rect(x - w * 0.012, y + h * 0.16, w * 0.016, h * 0.08, RIM, radius=2)
    cv.rect(x + w - w * 0.004, y + h * 0.2, w * 0.016, h * 0.12, RIM, radius=2)
    cv.rect(x, y, w, h, BODY, radius=r)
    cv.outline(x + 1, y + 1, w - 2, h - 2, RIM, width=2, radius=r - 1)
    box = Box(x + b, y + b, w - 2 * b, h - 2 * b)
    _screen(cv, screen, box, radius=r - b)
    cv.rect(x + w * 0.36, box.y + h * 0.012, w * 0.28, h * 0.026, BODY, radius=h * 0.013)  # the camera pill
    return box


def laptop_frame(cv, x, y, w, h, screen):
    """A plain, unbranded laptop filling (x, y, w, h) -- lid and base -- its
    screen showing `screen` (an image or a `screen(cv, box)` callable).
    Returns the screen Box."""
    lid_w, lid_h = w * 0.82, h * 0.93
    lx = x + (w - lid_w) / 2
    b = lid_w * 0.025
    cv.shadow(x, y, w, h, radius=14, dy=h * 0.05, blur=h * 0.1, color=(0, 0, 0, 0.55))
    cv.rect(lx, y, lid_w, lid_h, BODY, radius=lid_w * 0.025)
    cv.outline(lx + 1, y + 1, lid_w - 2, lid_h - 2, RIM, width=2, radius=lid_w * 0.025)
    box = Box(lx + b, y + b * 1.3, lid_w - 2 * b, lid_h - b * 2.3)
    _screen(cv, screen, box, radius=3)
    base_y, base_h = y + lid_h, h - lid_h
    cv.rect(x, base_y, w, base_h, METAL, radius=base_h / 2)
    cv.rect(x + w * 0.42, base_y, w * 0.16, base_h * 0.45, METAL_DARK, radius=base_h * 0.2)  # the thumb notch
    return box


FRAMES = {'phone': phone_frame, 'laptop': laptop_frame}


def device_slide_in(cv, kind, box, screen, p, side='bottom', distance=None, tilt=6.0, ease=vb.ease_out_quint):
    """Draw a `kind` device ('phone' or 'laptop') at progress `p` (0 -> 1)
    of its entrance into `box`, its resting place. It starts `distance` px
    off toward `side` ('bottom', 'top', 'left', 'right'; default: far
    enough to start just off frame) turned `tilt` degrees, and `ease(p)`
    carries it in, untilting as it lands. `screen` is an image or a
    `screen(cv, box)` callable. Returns the device's Box at rest.

    In a film: `device_slide_in(cv, 'phone', Box(...), shot_image, shot.f / 24, side='right')`."""
    box = Box(*box)
    if distance is None:
        distance = {'bottom': cv.height - box.y, 'top': box.bottom, 'left': box.right,
                    'right': cv.width - box.x}[side] + 40
    dx, dy = {'bottom': (0, 1), 'top': (0, -1), 'left': (-1, 0), 'right': (1, 0)}[side]
    q = 1 - ease(vb.clamp01(p))
    if q > 0.999:
        return box
    turn = math.radians(tilt) * q * (1 if side in ('bottom', 'left') else -1)
    ctx = cv.ctx
    ctx.save()
    ctx.translate(box.cx + dx * distance * q, box.cy + dy * distance * q)
    ctx.rotate(turn)
    ctx.translate(-box.cx, -box.cy)
    FRAMES[kind](cv, *box, screen)
    ctx.restore()
    if q < 0.01:
        cv.mark(kind, *box)
    return box


# ---- the demo ----

def _dashboard(cv, box):
    """A made-up analytics page for the laptop screen."""
    x, y, w, h = box
    cv.rect(x, y, w, h, '#f4f3ef')
    cv.rect(x, y, w * 0.2, h, '#1c1e25')
    for i in range(1, 5):
        cv.rect(x + w * 0.03, y + h * (0.14 + i * 0.1), w * 0.13, h * 0.035, '#7b818d', radius=4)
    cv.rect(x + w * 0.03, y + h * 0.14, w * 0.13, h * 0.035, demo.ACCENT, radius=4)
    cx = x + w * 0.24
    cv.rect(cx, y + h * 0.07, w * 0.3, h * 0.05, '#1c1e25', radius=5)
    tile_w = w * 0.23
    for i, c in enumerate((demo.ACCENT, demo.TEAL, '#e3b448')):
        tx = cx + i * (tile_w + w * 0.02)
        cv.rect(tx, y + h * 0.18, tile_w, h * 0.2, '#ffffff', radius=8)
        cv.rect(tx + tile_w * 0.1, y + h * 0.23, tile_w * 0.35, h * 0.04, '#7b818d', radius=3)
        cv.rect(tx + tile_w * 0.1, y + h * 0.3, tile_w * 0.6, h * 0.05, c, radius=4)
    chart = Box(cx, y + h * 0.44, w * 0.73, h * 0.49)
    cv.rect(*chart, '#ffffff', radius=8)
    bars = (0.35, 0.5, 0.42, 0.62, 0.55, 0.74, 0.68, 0.86, 0.8)
    bw = chart.w / (len(bars) * 1.6)
    for i, v in enumerate(bars):
        bh = chart.h * 0.75 * v
        cv.rect(chart.x + bw * 0.8 + i * bw * 1.6, chart.bottom - chart.h * 0.1 - bh, bw, bh,
                demo.TEAL if i < len(bars) - 1 else demo.ACCENT, radius=3)


def draw(n, cv):
    laptop = Box(demo.W / 2 - 330, demo.H / 2 - 170, 560, 350)
    phone = Box(laptop.right - 80, demo.H / 2 - 120, 140, 290)
    device_slide_in(cv, 'laptop', laptop, _dashboard, demo.phase(n, 0.3, 1.4), side='bottom')
    device_slide_in(cv, 'phone', phone, u.app_screen(), demo.phase(n, 1.0, 2.0), side='right',
                    ease=vb.ease_out_back)


TECHNIQUE = Technique(
    id='device-mockup-slide-in',
    name='Device mockup slide-in',
    family='broadcast',
    group='UI walkthroughs',
    aliases=('device mockup', 'mockup slide-in', 'phone slide-in', 'laptop mockup reveal'),
    definition='A drawn laptop or phone with the product on its screen glides in from off frame, '
               'straightening from a slight tilt as it settles into place.',
    phrasings=('slide our app in on a phone mockup',
               'bring a laptop up from the bottom with the dashboard on its screen',
               'show the screenshot inside a device that moves into the shot'),
    related=('uncover', 'circular-clip-reveal', 'zoom-out-reveal', 'fade-up-scroll-reveal', 'wireframe-reveal',
             'slide-over-cover'),
    api=('videobuilder.techniques.broadcast.device_mockup_slide_in.device_slide_in',
         'videobuilder.techniques.broadcast.device_mockup_slide_in.phone_frame',
         'videobuilder.techniques.broadcast.device_mockup_slide_in.laptop_frame'),
    demo=lambda: demo.film(draw),
)
