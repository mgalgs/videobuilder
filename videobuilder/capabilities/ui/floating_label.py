"""Floating label: a form field's label sits inside the empty box like a
placeholder, and when the field takes focus it shrinks and rises onto the
top border, where it stays while the value is typed underneath."""
import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ..schema import Technique


def label_at(box, font, p, lift=0.72, inset=28):
    """Where the label of a field `box` is at progress `p` (0 = resting
    inside, 1 = floated): `(x, y, scale)`, the top-left of the label line and
    its size against `font`. At rest it is vertically centred `inset` in from
    the left; floated it is `lift` of its size, centred on the top border."""
    p = vb.clamp01(p)
    h = vb.text.line_height(font)
    x = box.x + inset
    y0 = box.y + (box.h - h) / 2
    y1 = box.y - h * lift / 2
    s = 1 + (lift - 1) * p
    return x, y0 + (y1 - y0) * p, s


def draw_floating_label(cv, box, label, font, p, rest=kit.MUTED, focus=kit.TEAL, background=kit.BG,
                        lift=0.72, inset=28, border=3, radius=14):
    """An outlined field `box` with its `label` floated by progress `p` (run
    it 0 -> 1 with an ease over ~0.3 s on focus, and back to 0 on blur if the
    field is still empty). The border and label shift from `rest` to `focus`
    colour as it rises, and a `background` notch opens in the border behind
    the floated label. Returns the label's Box."""
    p = vb.clamp01(p)
    color = kit.mix(rest, focus, p)
    cv.outline(box.x, box.y, box.w, box.h, kit.mix(kit.LINE, focus, p) if p else rest,
               width=border + p, radius=radius, alpha=1.0 if p else 0.6)
    x, y, s = label_at(box, font, p, lift, inset)
    w, h = vb.text.block_size([label], font)
    if p > 0:
        pad = 10 * s
        notch = (w * s + 2 * pad) * min(1, p * 1.6)
        cv.rect(x + w * s / 2 - notch / 2, box.y - border * 2, notch, border * 4, background)
    with cv.layer(dx=x, dy=y, scale=s):
        vb.text.draw(cv, [label], font, 0, 0, color)
    return vb.Box(x, y, w * s, h * s)


LABEL, VALUE = 'Email address', 'ada@lovelace.dev'


def draw(n, cv):
    font = demo.font(44, 500)
    w, h = 820, 120
    box = vb.Box((demo.W - w) / 2, (demo.H - h) / 2, w, h)
    p = vb.ease_out_quint(demo.phase(n, 0.6, 1.2))
    cv.shadow(box.x, box.y, box.w, box.h, radius=14, dy=8, blur=26, color=(0, 0, 0, 0.35))
    cv.mark('label', *draw_floating_label(cv, box, LABEL, font, p))
    t = n / demo.FPS
    typed = VALUE[:max(0, int((t - 1.25) * 16))]
    vf = demo.font(48, 600)
    tx, ty = box.x + 28, box.y + (box.h - vb.text.line_height(vf)) / 2 + 4
    if typed:
        vb.text.draw(cv, [typed], vf, tx, ty, demo.INK)
    if p > 0.9 and (len(typed) < len(VALUE) or int(t * 2.2) % 2 == 0):  # caret: steady while typing, then blinks
        cx = tx + vb.text.measure(typed, vf) + 4
        cv.rect(cx, ty + 6, 4, vb.text.line_height(vf) - 12, demo.TEAL)


TECHNIQUE = Technique(
    id='floating-label',
    name='Floating label',
    family='ui',
    group='Forms',
    aliases=('float label', 'animated input label', 'material text field label'),
    definition='A text field\'s label starts inside the empty box like a hint, then shrinks and slides up '
               'onto the field\'s top edge when the field is selected, leaving room for the typed value.',
    phrasings=('the placeholder moves up and gets smaller when you click into the input',
               'an input box whose label jumps to the border as you start typing',
               'form field where the hint text floats above the box on focus'),
    related=('idle-float-bob', 'letter-roll', 'floating-reaction-emoji', 'decimal-counter-with-formatting',
             'dock-magnification', 'liquid-fill-level'),
    api=('videobuilder.techniques.ui.floating_label.draw_floating_label',
         'videobuilder.techniques.ui.floating_label.label_at'),
    demo=lambda: demo.film(draw),
)
