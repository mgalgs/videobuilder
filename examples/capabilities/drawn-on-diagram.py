"""Capability: drawn-on diagram. A small whiteboard diagram -- three boxes,
two arrows, two icons -- draws on stroke by stroke with a little hand jitter
(`videobuilder.paths.jitter`), the camera tracking each stroke on a board
bigger than the frame (`cv.layer` as the camera), then pulling back to show
the whole board at once.

    python -m videobuilder preview examples/capabilities/drawn-on-diagram.py

LOOP = True: both ends rest on the same pulled-back, empty board. One
forward pass (frame index `vf`, 0..FORWARD_TOTAL) drives both halves of the
clip: played forward it draws the board and pulls back; during HOLD it
stays at `vf = FORWARD_TOTAL`; then it is replayed with `vf` counting back
down to 0, erasing the board in reverse -- the same trick bar-charts.py uses
to grow and shrink its bars from one function of `n`.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import Box, paths, text  # noqa: E402

LOOP = True
FPS = 30
START, TAIL = 4, 4

BOX_W, BOX_H = 230, 150
Y_TOP = 380
MID_Y = Y_TOP + BOX_H / 2
BOX1_X, BOX2_X, BOX3_X = 90, 560, 1030


def rect_points(x, y, w, h, n=48):
    return paths.resample([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], n, closed=True)


BOX1 = rect_points(BOX1_X, Y_TOP, BOX_W, BOX_H)
BOX2 = rect_points(BOX2_X, Y_TOP, BOX_W, BOX_H)
BOX3 = rect_points(BOX3_X, Y_TOP, BOX_W, BOX_H)

# A small "data in" chevron inside box 1, and a checkmark inside box 3.
ICON1 = [(BOX1_X + 95, Y_TOP + 50), (BOX1_X + 115, Y_TOP + 75), (BOX1_X + 95, Y_TOP + 100)]
ICON2 = [(BOX3_X + 85, Y_TOP + 78), (BOX3_X + 105, Y_TOP + 100), (BOX3_X + 150, Y_TOP + 55)]

ARROW1_SHAFT = [(BOX1_X + BOX_W, MID_Y), (BOX2_X, MID_Y)]
ARROW1_HEAD = [(BOX2_X - 18, MID_Y - 12), (BOX2_X + 3, MID_Y), (BOX2_X - 18, MID_Y + 12)]
ARROW2_SHAFT = [(BOX2_X + BOX_W, MID_Y), (BOX3_X, MID_Y)]
ARROW2_HEAD = [(BOX3_X - 18, MID_Y - 12), (BOX3_X + 3, MID_Y), (BOX3_X - 18, MID_Y + 12)]

LABEL_F = _kit.font(44, 650)

BANDS = (
    dict(name='box1', dur=9, label=('Input', BOX1_X, Y_TOP + BOX_H + 26),
         strokes=(('box1', BOX1, True), ('icon1', ICON1, False))),
    dict(name='arrow1', dur=6, label=None,
         strokes=(('arrow1-shaft', ARROW1_SHAFT, False), ('arrow1-head', ARROW1_HEAD, False))),
    dict(name='box2', dur=9, label=('Process', BOX2_X, Y_TOP + BOX_H + 26),
         strokes=(('box2', BOX2, True),)),
    dict(name='arrow2', dur=6, label=None,
         strokes=(('arrow2-shaft', ARROW2_SHAFT, False), ('arrow2-head', ARROW2_HEAD, False))),
    dict(name='box3', dur=9, label=('Done', BOX3_X, Y_TOP + BOX_H + 26),
         strokes=(('box3', BOX3, True), ('icon2', ICON2, False))),
    dict(name='pullback', dur=9, label=None, strokes=()),
)
CUM = [0]
for _b in BANDS:
    CUM.append(CUM[-1] + _b['dur'])
FORWARD_TOTAL = CUM[-1]
HOLD = 12
TOTAL = START + FORWARD_TOTAL + HOLD + FORWARD_TOTAL + TAIL

# The box labels sit inside the diagram's own content area by construction.
OVERLAP_OK = {('diagram', 'label-box1'), ('diagram', 'label-box2'), ('diagram', 'label-box3')}

# Hand jitter, deterministic per stroke, baked in once at import: every
# frame that draws a stroke draws the same wobble, not a new one.
JITTERED = {name: paths.jitter(pts, seed=i, amount=2.2, wander=0.4)
           for i, (name, pts, closed) in enumerate(s for b in BANDS for s in b['strokes'])}
CLOSED = {name: closed for b in BANDS for name, pts, closed in b['strokes']}

ALL_POINTS = [p for pts in JITTERED.values() for p in pts]
_bx0, _by0 = min(p[0] for p in ALL_POINTS), min(p[1] for p in ALL_POINTS)
_bx1, _by1 = max(p[0] for p in ALL_POINTS), max(p[1] for p in ALL_POINTS)
BOARD_BBOX = (_bx0, _by0 - 10, _bx1 - _bx0, _by1 - _by0 + 70)   # +70 leaves room for labels below


def bbox_of(points, pad=46):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs) - pad, min(ys) - pad, max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad


def target_for(content, bbox, max_scale=2.0, min_scale=0.0):
    x, y, w, h = bbox
    scale = min(content.w / w, content.h / h)
    scale = max(min_scale, min(max_scale, scale))
    return x + w / 2, y + h / 2, scale


def camera_lerp(a, b, p):
    return tuple(av + (bv - av) * p for av, bv in zip(a, b))


def find_band(vf):
    """(band index, local progress 0..1 eased) for a forward-progress value."""
    for i, b in enumerate(BANDS):
        if vf < CUM[i + 1] or i == len(BANDS) - 1:
            local = vb.interpolate(vf, [CUM[i], CUM[i + 1]], [0, 1], ease=vb.ease_in_out_quart)
            return i, local
    return len(BANDS) - 1, 1.0


def draw(n, cv):
    cv.fill(_kit.BG)
    s = _kit.safe(cv, 64)
    title_f = _kit.font(32, 700)
    _kit.text_marked(cv, 'title', text.wrap('Drawn-on diagram', title_f, s.w), title_f, s.x, s.y, _kit.INK)
    content = Box(s.x, s.y + 92, s.w, s.bottom - (s.y + 92))
    cv.mark('diagram', *content)

    if n < START:
        vf = 0
    elif n < START + FORWARD_TOTAL:
        vf = n - START
    elif n < START + FORWARD_TOTAL + HOLD:
        vf = FORWARD_TOTAL
    elif n < START + FORWARD_TOTAL + HOLD + FORWARD_TOTAL:
        vf = FORWARD_TOTAL - (n - (START + FORWARD_TOTAL + HOLD))
    else:
        vf = 0

    band_i, local = find_band(vf)
    wide_target = target_for(content, BOARD_BBOX, max_scale=1.0)

    targets = [wide_target]
    for b in BANDS[:-1]:
        all_pts = [p for name, _, _ in b['strokes'] for p in JITTERED[name]]
        targets.append(target_for(content, bbox_of(all_pts)) if all_pts else targets[-1])
    # band i (content bands) eases the camera from the previous target to its own;
    # the pullback band eases from the last content target back to the wide one.
    prev_t = targets[band_i] if band_i < len(BANDS) - 1 else targets[-1]
    this_t = targets[band_i + 1] if band_i < len(BANDS) - 1 else wide_target
    cam = camera_lerp(prev_t, this_t, local)

    with cv.layer(dx=content.cx - cam[0] * cam[2], dy=content.cy - cam[1] * cam[2], scale=cam[2]):
        for i, b in enumerate(BANDS):
            if i > band_i or not b['strokes']:
                continue
            frac = 1.0 if i < band_i else local
            for name, _, _ in b['strokes']:
                # reveal() already appends the closing point when frac reaches 1
                # and closed=True; stroking it as open avoids a chord back to the
                # start corner while the stroke is still only partly drawn on.
                revealed = paths.reveal(JITTERED[name], frac, closed=CLOSED[name])
                paths.draw(cv, revealed, _kit.INK, width=6, closed=False)
            if b['label']:
                word, lx, ly = b['label']
                label_p = vb.clamp01((frac - 0.6) / 0.4)
                if i < band_i:
                    label_p = 1.0
                if label_p > 0.01:
                    local_box = text.draw(cv, [word], LABEL_F, lx, ly, _kit.ACCENT, alpha=label_p)
                    # The tracking camera can leave an earlier band's label outside
                    # the frame while it follows a later stroke; only mark it when
                    # it actually lands on screen, so checks don't flag content
                    # nobody can see.
                    corners = [(local_box.x, local_box.y), (local_box.right, local_box.y),
                               (local_box.x, local_box.bottom), (local_box.right, local_box.bottom)]
                    screen_pts = [(content.cx + (wx - cam[0]) * cam[2], content.cy + (wy - cam[1]) * cam[2])
                                  for wx, wy in corners]
                    sx0, sy0 = min(p[0] for p in screen_pts), min(p[1] for p in screen_pts)
                    sx1, sy1 = max(p[0] for p in screen_pts), max(p[1] for p in screen_pts)
                    screen_box = Box(sx0, sy0, sx1 - sx0, sy1 - sy0)
                    if screen_box.intersects(Box.of(cv)):
                        cv.mark(f"label-{b['name']}", *local_box)


FILM = vb.Film(draw=draw, fps=FPS, frames=TOTAL, formats=(_kit.FORMAT,), background=_kit.BG,
               keyframes=((START + CUM[2] - 2, 'box 2 drawn'),
                          (START + FORWARD_TOTAL + HOLD // 2, 'pulled back, whole board')))

if __name__ == '__main__':
    vb.main(__file__)
