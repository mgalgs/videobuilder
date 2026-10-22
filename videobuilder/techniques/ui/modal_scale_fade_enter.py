"""Modal Scale-Fade Enter: a dimming backdrop fades in over the page while a
dialog grows from just under full size to full size about its centre,
fading in as it goes."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def modal_enter(cv, p, dialog, cx, cy, from_scale=0.9, backdrop='#000000', dim=0.6, ease=vb.ease_out_quint):
    """Draw the modal's entrance at progress `p` (0 -> 1) over whatever is
    already on `cv`: the backdrop `backdrop` fades up to alpha `dim` across
    the whole of `p`, and `dialog(cv)` -- drawn at its resting size and place
    -- scales from `from_scale` to 1 about (cx, cy) and fades from 0 to 1,
    both on `ease`. At `p >= 1` this is the open modal at rest.

    In a film, draw the page, then call it with the frames since the modal
    opened, e.g. `modal_enter(cv, (n - open_at) / 9, my_dialog, W / 2, H / 2)`."""
    p = vb.clamp01(p)
    if p <= 0:
        return
    cv.fill(backdrop, alpha=dim * p)
    e = ease(p)
    s = from_scale + (1 - from_scale) * e
    with cv.layer(opacity=vb.clamp01(e), dx=cx * (1 - s), dy=cy * (1 - s), scale=s):
        dialog(cv)


def _page(cv):
    """A plain app screen behind the modal: a top bar and a grid of cards."""
    cv.rect(0, 0, demo.W, 64, demo.LINE)
    demo.word(cv, 'Projects', 120, 32, size=26, weight=700)
    cv.rect(demo.W - 170, 16, 130, 34, demo.ACCENT, radius=17)
    for i in range(3):
        for j in range(2):
            demo.card(cv, 180 + i * 300, 190 + j * 210, w=250, h=160, color=(demo.TEAL, '#3a3d47')[(i + j) % 2])


DW, DH = 440, 250


def _dialog(cv):
    """The dialog at rest, centred in the frame: title, a line of body text,
    and two buttons."""
    x, y = (demo.W - DW) / 2, (demo.H - DH) / 2
    cv.shadow(x, y, DW, DH, radius=20, dy=18, blur=40, color=(0, 0, 0, 0.6))
    cv.rect(x, y, DW, DH, '#22242b', radius=20)
    cv.outline(x, y, DW, DH, '#3a3d47', width=1.5, radius=20)
    vb.text.draw(cv, ['Delete this project?'], demo.font(30, 800), x + 32, y + 32, demo.INK)
    cv.rect(x + 32, y + 92, DW * 0.72, 12, demo.MUTED, radius=6, alpha=0.6)
    cv.rect(x + 32, y + 116, DW * 0.5, 12, demo.MUTED, radius=6, alpha=0.6)
    cv.rect(x + DW - 300, y + DH - 72, 120, 44, '#3a3d47', radius=12)
    cv.rect(x + DW - 164, y + DH - 72, 132, 44, demo.ACCENT, radius=12)
    demo.word(cv, 'Cancel', x + DW - 240, y + DH - 50, size=20, weight=700)
    demo.word(cv, 'Delete', x + DW - 98, y + DH - 50, size=20, weight=700)
    cv.mark('dialog', x, y, DW, DH)


def draw(n, cv):
    _page(cv)
    modal_enter(cv, demo.phase(n, 0.8, 1.6), _dialog, demo.W / 2, demo.H / 2, from_scale=0.85)


TECHNIQUE = Technique(
    id='modal-scale-fade-enter',
    name='Modal scale-fade enter',
    family='ui',
    group='Overlays & menus',
    aliases=('dialog pop-in', 'modal zoom', 'modal open'),
    definition='A pop-up box opens by growing from a little under full size while it fades in, '
               'as the screen behind it darkens.',
    phrasings=('make the dialog pop open over a dimmed screen',
               'the confirm box fades and grows in while the page behind goes dark',
               'open a modal with a little zoom and fade'),
    related=('scale-zoom-through', 'image-hover-zoom', 'ui-walkthrough-camera-zoom', 'zoom-through',
             'callout-highlight', 'zoom-out-reveal'),
    api=('videobuilder.techniques.ui.modal_scale_fade_enter.modal_enter', 'videobuilder.ease_out_quint'),
    demo=lambda: demo.film(draw),
)
