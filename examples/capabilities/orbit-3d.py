"""Capability: a pre-rendered 3D clip composited like any other image.
`examples/assets/orbit.mp4` (720x1280, 30 fps, 60 frames) decoded frame by
frame and drawn into a square region of the canvas with `cv.image`, under a
small unobtrusive caption -- the clip IS the hero move here, nothing else
competes with it.

    python -m videobuilder preview examples/capabilities/orbit-3d.py

LOOP = True: the source clip's own orbit repeats every 30 of its frames
(checked by diffing decoded frames -- frame 30 is within noise of frame 0,
while frame 29 -> frame 0 is the same size step as any other single-frame
step). At 30 fps on both sides, local frame `n` maps 1:1 to clip frame
`n % 30`, so the loop is a true period, not a disclosed seam.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import text  # noqa: E402

LOOP = True
TOTAL = 90   # 3.0 s = 3 full cycles of the clip's own 30-frame (1.0 s) orbit

CLIP = vb.Clip(str(_kit.HERE.parent / 'assets' / 'orbit.mp4'))
CLIP_PERIOD = 30   # the clip's own loop period, in its own frames (checked by hand)

CAPTION_F = _kit.font(20, 600)

BOX_SIZE = 560
BOX_X = (720 - BOX_SIZE) / 2
BOX_Y = 64
CLIP_W, CLIP_H = CLIP.size   # 720 x 1280: portrait, taller than our square box

# `cv.image` stretches to the exact box, so a plain call would squash a 9:16
# source into a 1:1 box. Scale the clip up to "cover" the square box instead
# (aspect preserved, centred, clipped to the box) and only then stretch.
_COVER = max(BOX_SIZE / CLIP_W, BOX_SIZE / CLIP_H)
_DRAW_W, _DRAW_H = CLIP_W * _COVER, CLIP_H * _COVER
_DRAW_X, _DRAW_Y = BOX_X - (_DRAW_W - BOX_SIZE) / 2, BOX_Y - (_DRAW_H - BOX_SIZE) / 2


def draw(n, cv):
    cv.fill(_kit.BG)
    clip_frame = CLIP.frame(n % CLIP_PERIOD)
    with cv.clip(BOX_X, BOX_Y, BOX_SIZE, BOX_SIZE):
        cv.image(clip_frame, _DRAW_X, _DRAW_Y, _DRAW_W, _DRAW_H)
    cv.mark('render', BOX_X, BOX_Y, BOX_SIZE, BOX_SIZE)

    bar_h = 56
    bar_y = cv.height - bar_h
    cv.rect(0, bar_y, cv.width, bar_h, _kit.BG)
    cap = text.wrap('3D render, composited like any image', CAPTION_F, 500)
    cw, ch = text.block_size(cap, CAPTION_F)
    _kit.text_marked(cv, 'caption', cap, CAPTION_F, cv.width / 2 - cw / 2, bar_y + bar_h / 2 - ch / 2,
                      _kit.MUTED, align='center', width=500)


FILM = vb.Film(draw=draw, fps=30, frames=TOTAL, formats=(_kit.FORMAT,), background=_kit.BG,
               keyframes=(0, 15, 45, 75))

if __name__ == '__main__':
    vb.main(__file__)
