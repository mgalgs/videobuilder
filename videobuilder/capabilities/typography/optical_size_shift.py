"""Optical Size Shift: a variable font's optical-size (`opsz`) axis moves, so
the same letters redraw themselves for small text or for display -- sturdier,
looser and more open at the text end; finer, tighter and crisper at the
display end. `vb.Font` drives only the weight axis, so `OpticalFont` here adds
`opsz`; the bundled Inter has the axis, from 14 to 32."""
import dataclasses

import videobuilder as vb

from ... import fonts
from .. import _demo as demo
from ..schema import Technique

OPSZ_TEXT, OPSZ_DISPLAY = 14.0, 32.0  # the bundled Inter's opsz range
_registered = []


@dataclasses.dataclass(frozen=True)
class OpticalFont(vb.Font):
    """A `vb.Font` that also sets the `opsz` axis. `opsz=None` follows the
    size, as browsers' `font-optical-sizing: auto` does (the font clamps it to
    its own range)."""
    opsz: float | None = None

    def description(self):
        d = super().description()
        d.set_variations(f'wght={self.weight},opsz={self.size if self.opsz is None else self.opsz:g}')
        return d


def optical_font(size, weight=700, opsz=None, family='Inter', **kw):
    """An `OpticalFont`; the bundled Inter (which has an `opsz` axis) is
    registered on first use. `kw` goes to `vb.Font` (tracking, style...)."""
    if family == 'Inter' and not _registered:
        vb.text.register(fonts.path('inter'))
        _registered.append(family)
    return OpticalFont(family, size, weight=weight, opsz=opsz, **kw)


def optical_size_shift(font, p, start=OPSZ_TEXT, end=OPSZ_DISPLAY):
    """`font` with its optical size at progress `p` (0 -> 1) from `start` to
    `end`, size unchanged: the letterforms re-tune while the type stays put.
    A plain `vb.Font` becomes an `OpticalFont`."""
    if not isinstance(font, OpticalFont):
        font = OpticalFont(**{f.name: getattr(font, f.name) for f in dataclasses.fields(vb.Font)})
    return dataclasses.replace(font, opsz=start + (end - start) * vb.clamp01(p))


def draw(n, cv):
    p = vb.ease_in_out_quart(demo.phase(n, 0.5, 1.6)) - vb.ease_in_out_quart(demo.phase(n, 2.0, 2.8))
    f = optical_size_shift(optical_font(170, 700), p)
    text = 'Optical'
    w, h = vb.text.block_size([text], f)
    x, y = (demo.W - w) / 2, demo.H / 2 - h / 2 - 30
    box = vb.text.draw(cv, [text], f, x, y, demo.INK)
    cv.mark('text', *box)
    # Brackets at the word's edges, so the spacing tightening reads.
    for bx in (x - 14, x + w + 14):
        cv.line(bx, y + 10, bx, y + h - 10, demo.ACCENT, width=3, alpha=0.8)
    # The axis: a track from text to display, its knob at the current opsz.
    tx0, tx1, ty = demo.W / 2 - 220, demo.W / 2 + 220, demo.H / 2 + h / 2 + 40
    cv.line(tx0, ty, tx1, ty, demo.LINE, width=4)
    demo.dot(cv, tx0 + (tx1 - tx0) * p, ty, r=11, color=demo.ACCENT)
    small = demo.mono(20, 500)
    for label, lx in (('text 14', tx0), ('display 32', tx1)):
        lw, _ = vb.text.block_size([label], small)
        vb.text.draw(cv, [label], small, lx - lw / 2, ty + 22, demo.MUTED)
    demo.word(cv, f'opsz {f.opsz:.0f}', demo.W / 2, ty - 26, size=22, color=demo.TEAL, font=small)


TECHNIQUE = Technique(
    id='optical-size-shift',
    name='Optical size shift',
    family='typography',
    group='Variable font',
    aliases=('opsz axis animation', 'size-adaptive type', 'optical sizing'),
    definition='A word stays the same size while its variable font slides along the optical-size axis, '
               'its letters tightening and sharpening for headlines or opening up and thickening for small text.',
    phrasings=('the letters retune themselves from body-text shapes into headline shapes',
               'animate the font\'s optical size so the spacing tightens and the strokes get finer',
               'the type morphs between its small-print and display versions without changing size'),
    related=('axis-rescale', 'optical-zoom', 'tilt-shift-miniature', 'dot-matrix-text', 'chart-type-morph',
             'op-art-vibrating-pattern'),
    api=('videobuilder.techniques.typography.optical_size_shift.optical_size_shift',
         'videobuilder.techniques.typography.optical_size_shift.optical_font',
         'videobuilder.techniques.typography.optical_size_shift.OpticalFont'),
    demo=lambda: demo.film(draw),
)
