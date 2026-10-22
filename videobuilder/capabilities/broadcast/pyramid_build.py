"""Pyramid build: a triangle cut into horizontal tiers assembles itself one
tier at a time, wide base first, each band dropping onto the one below with
its label, until the apex caps the stack."""
import videobuilder as vb

from ...canvas import rgba
from .. import _demo as demo
from ..schema import Capability


def tier_arrivals(count, p, overlap=1.5, ease=vb.ease_out_back):
    """Each of `count` tiers' arrival progress at overall progress `p`, base
    first: tier 0 (the base) starts at `p = 0`, the apex finishes at `p = 1`.
    Each arrival lasts `overlap / count` of the build, so neighbours overlap
    when `overlap > 1`. Values can overshoot 1 with an overshooting `ease`."""
    if count <= 0:
        return []
    d = min(1.0, overlap / count)
    starts = [0.0] * count if count == 1 else [k * (1 - d) / (count - 1) for k in range(count)]
    return [ease(vb.clamp01((p - s) / d)) if p > s else 0.0 for s in starts]


def _band(cv, pts, color, alpha):
    c = cv.ctx
    c.move_to(*pts[0])
    for pt in pts[1:]:
        c.line_to(*pt)
    c.close_path()
    c.set_source_rgba(*rgba(color, alpha))
    c.fill()


def draw_pyramid(cv, cx, base_y, width, height, p, labels=(), colors=None, count=None, gap=8, drop=None,
                 font=None, ink=demo.INK, **kw):
    """Draw a pyramid of `count` tiers (default `len(labels)`) standing on
    `base_y`, centred on `cx`, `width` wide at the base and `height` tall,
    built bottom-up at progress `p` (0 -> 1). Each tier is a trapezoid slice
    of the triangle (the top one a triangle) separated by `gap` px; it falls
    `drop` px (default one tier height) into place while fading in, and its
    label (`labels` listed base first) is centred on it. `colors` gives one
    colour per tier, base first, cycling. `kw` goes to `tier_arrivals`.
    Returns the Box of the finished pyramid."""
    labels = tuple(labels)
    count = count or len(labels)
    colors = colors or (demo.ACCENT, demo.TEAL)
    font = font or demo.font(28, 800)
    step = height / count
    drop = step if drop is None else drop
    half = width / 2

    def half_at(y):  # half-width of the triangle at height y above the base
        return half * (1 - y / height)

    for k, a in enumerate(tier_arrivals(count, p, **kw)):
        if a <= 0:
            continue
        lo, hi = k * step + (gap / 2 if k else 0), (k + 1) * step - (gap / 2 if k < count - 1 else 0)
        dy = -(1 - a) * drop                       # above its seat until it lands (dips below on overshoot)
        y0, y1 = base_y - lo + dy, base_y - hi + dy
        w0, w1 = half_at(lo), half_at(hi)
        pts = [(cx - w0, y0), (cx + w0, y0), (cx + w1, y1), (cx - w1, y1)]
        alpha = vb.clamp01(a * 2)
        _band(cv, pts, colors[k % len(colors)], alpha)
        if k < len(labels):
            demo.word(cv, labels[k], cx, (y0 + y1) / 2 + (step * 0.12 if k == count - 1 else 0),
                      font=font, color=ink, alpha=vb.clamp01(a * 2 - 0.6))
    return vb.Box(cx - half, base_y - height, width, height)


LABELS = ('Foundation', 'Structure', 'Growth', 'Peak')


def draw(n, cv):
    colors = ('#3a3d47', '#4a7f86', demo.TEAL, demo.ACCENT)
    box = draw_pyramid(cv, demo.W / 2, demo.H - 70, 620, 400, demo.phase(n, 0.25, 2.3), LABELS,
                       colors=colors, font=demo.font(26, 800))
    cv.mark('pyramid', *box)


CAPABILITY = Capability(
    id='pyramid-build',
    name='Pyramid build',
    family='broadcast',
    group='Process diagrams',
    aliases=('pyramid diagram', 'hierarchy pyramid', 'tiered triangle build', 'layered pyramid chart'),
    definition='A triangle split into labelled horizontal layers assembles from the wide base upward, '
               'each layer dropping onto the one below until the point on top completes it.',
    phrasings=('build a pyramid chart one level at a time from the bottom',
               'stack the layers of a hierarchy triangle up to the top',
               'show a tiered pyramid diagram assembling with labels on each band'),
    related=('stacked-bar-build', 'shape-stacking-drop', 'stacked-line-build', 'voxel-build',
             'exploded-view', 'isometric-bar-rise'),
    api=('videobuilder.capabilities.broadcast.pyramid_build.draw_pyramid',
         'videobuilder.capabilities.broadcast.pyramid_build.tier_arrivals'),
    demo=lambda: demo.film(draw),
)
