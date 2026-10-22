"""Paper Fold Reveal: a sheet starts folded up into one panel, blank side
out, then opens panel by panel, each one swinging over on its crease in
perspective until the whole sheet lies flat and its content is showing."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _smooth(t):
    t = vb.clamp01(t)
    return t * t * (3 - 2 * t)


def paper_fold_reveal(cv, content, x, y, w, h, p, panels=3, direction='right', back='#d8d2c4',
                      shade=0.5, crease=0.18, focal=1400, strips=24):
    """Unfold the sheet (x, y, w, h) at progress `p` (0 -> 1). `content(cv)`
    draws the sheet's face in frame coordinates, inside that box; the fold
    only clips and transforms it, so any drawing (text, a photo, a card)
    works. The sheet is cut into `panels` equal panels along `direction`
    ('right' opens like a brochure, 'down' like a letter), all folded onto
    the first at 0, which shows its blank `back`; then each panel in turn
    turns over its crease, back side up until it passes upright, face up after.

    `shade` darkens a panel as it turns away from the viewer, `crease`
    marks the folds once flat, `focal` sets the perspective (smaller is
    stronger) and `strips` how finely a turning panel is sliced to draw it.
    Returns the Box the sheet would cover when fully open."""
    if panels < 2:
        raise ValueError('paper_fold_reveal needs at least two panels')
    if direction not in ('right', 'down'):
        raise ValueError(f"direction must be 'right' or 'down', not {direction!r}")
    across = direction == 'down'  # the fold axis runs across x when opening downward
    size = (h if across else w) / panels
    cx, cy = x + w / 2, y + h / 2
    turns = [0.0] + [math.pi * (1 - _smooth(p * (panels - 1) - (k - 1))) for k in range(1, panels)]

    def point(k, d, v, angle):
        """Screen position of the spot `d` along panel k from its crease and `v` across it."""
        start = (y if across else x) + k * size
        a, z = start + d * math.cos(angle), d * math.sin(angle)
        f = focal / (focal - z)
        if across:
            return cx + (v - cx) * f, cy + (a - cy) * f
        return cx + (a - cx) * f, cy + (v - cy) * f

    def outline(k, angle, d0=0.0, d1=size):
        lo, hi = (x, x + w) if across else (y, y + h)
        return [point(k, d0, lo, angle), point(k, d0, hi, angle), point(k, d1, hi, angle), point(k, d1, lo, angle)]

    def fill(pts, color, alpha=1.0):
        c = cv.ctx
        c.move_to(*pts[0])
        for q in pts[1:]:
            c.line_to(*q)
        c.close_path()
        c.set_source_rgba(*vb.rgba(color, alpha))
        c.fill()

    # The face is drawn once, flat, then painted through each strip: drawing text
    # under a squashed transform would lay it out afresh and break up the words.
    printed = vb.Canvas(w, h, scale=cv.scale, format=cv.format)
    printed.ctx.translate(-x, -y)
    content(printed)

    def face(k, angle):
        """Panel k's printed side, turned `angle` off flat, drawn as thin
        affine strips so the far edge narrows in perspective."""
        c = cv.ctx
        start = (y if across else x) + k * size
        mid = cx if across else cy
        n = 1 if angle == 0 else strips
        for j in range(n):
            d0, d1 = size * j / n, size * (j + 1) / n
            a0, a1 = (point(k, d, mid, angle)[1 if across else 0] for d in (d0, d1))
            s = (a1 - a0) / (d1 - d0)
            f = focal / (focal - (d0 + d1) / 2 * math.sin(angle))
            seam = 0.6 / max(abs(s), 1e-3) if j < n - 1 else 0  # overlap strips so no hairline gaps show
            c.save()
            if across:
                c.transform(cairo.Matrix(f, 0, 0, s, cx - cx * f, a0 - (start + d0) * s))
                c.rectangle(x, start + d0, w, d1 - d0 + seam)
            else:
                c.transform(cairo.Matrix(s, 0, 0, f, a0 - (start + d0) * s, cy - cy * f))
                c.rectangle(start + d0, y, d1 - d0 + seam, h)
            c.clip()
            c.translate(x, y)
            c.scale(1 / cv.scale, 1 / cv.scale)
            c.set_source_surface(printed.surface, 0, 0)
            c.paint()
            c.restore()

    moving = next((k for k in range(1, panels) if 0 < turns[k] < math.pi), None)
    shown = [k for k in range(panels) if turns[k] == 0]
    flat_to = (max(shown) + 1) * size
    cv.shadow(x, y, w if across else flat_to, flat_to if across else h, dy=12, blur=30,
              color=(0, 0, 0, 0.45))
    for k in shown:
        covered = k + 1 < panels and turns[k + 1] == math.pi
        if covered:
            fill(outline(k, 0), back)
        else:
            face(k, 0)
    for k in shown[1:]:
        cv.line(*point(k, 0, x if across else y, 0), *point(k, 0, x + w if across else y + h, 0),
                '#000000', width=2, alpha=crease)
    if moving is not None:
        angle = turns[moving]
        pts = outline(moving, angle)
        if angle < math.pi / 2:
            face(moving, angle)
            fill(pts, '#000000', shade * angle / (math.pi / 2))
        else:
            fill(pts, back)
            fill(pts, '#000000', shade * (math.pi - angle) / (math.pi / 2))
    return vb.Box(x, y, w, h)


SHEET_W, SHEET_H, PANELS = 660, 360, 3
PAPER = '#f4f1ea'


def sheet(cv, x, y):
    """The demo's printed sheet: a headline across all three panels and a block in each."""
    cv.rect(x, y, SHEET_W, SHEET_H, PAPER)
    col = SHEET_W / PANELS
    for i, color in enumerate((demo.ACCENT, demo.TEAL, '#e8b04a')):
        cv.rect(x + col * i + 30, y + 200, col - 60, 120, color, radius=10)
    demo.word(cv, 'UNFOLDED', x + SHEET_W / 2, y + 110, size=92, color=demo.BG, weight=900)


def draw(n, cv):
    p = demo.phase(n, 0.4, 2.4)
    spread = SHEET_W / PANELS * (1 + (PANELS - 1) * _smooth(p))  # keep the visible part centred
    x, y = (demo.W - spread) / 2, (demo.H - SHEET_H) / 2
    box = paper_fold_reveal(cv, lambda c: sheet(c, x, y), x, y, SHEET_W, SHEET_H, p, panels=PANELS)
    cv.mark('sheet', *box)


CAPABILITY = Capability(
    id='paper-fold-reveal',
    name='Paper fold reveal',
    family='shapes',
    group='Cut-out & paper',
    aliases=('unfold reveal', 'fold-out reveal', 'brochure unfold', 'paper unfold'),
    definition='A folded sheet opens out one panel at a time, each flap swinging over its crease '
               'in perspective, until the flattened page shows what is printed on it.',
    phrasings=('have the card unfold like a folded piece of paper to show the content',
               'open it up like a tri-fold brochure, one flap after another',
               'the message is folded up at first and then unfolds to reveal itself'),
    related=('origami-fold', 'accordion-fold-text', 'accordion-fold', 'corner-wipe', 'crumple',
             'word-flip-in'),
    api=('videobuilder.capabilities.shapes.paper_fold_reveal.paper_fold_reveal',),
    demo=lambda: demo.film(draw),
)
