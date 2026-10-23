"""Frame Interpolation: motion recorded at a low frame rate is filled in with
made-up in-between frames, so a move that stuttered from pose to pose plays
back smooth at the output rate."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def frame_interpolation(cv, draw_at, t, source_fps, mode='motion'):
    """Draw the scene `draw_at(cv, s)` (time `s` in seconds) at output time `t`
    as if it only existed at `source_fps` frames a second, with the gaps
    between those source frames filled by `mode`:

    - 'hold': no interpolation, each source frame held until the next (the
      choppy original, for a before/after);
    - 'blend': frame blending, the two neighbouring source frames
      cross-faded by how far `t` sits between them, (1 - w) of the earlier
      plus w of the later, so it holds whether `draw_at` paints an opaque
      backdrop or a lone sprite on a shared one (soft, ghosts on fast moves);
    - 'motion': motion-compensated in-betweens, the scene evaluated where it
      would really be at `t` (what optical-flow retiming aims for).

    In a film: `frame_interpolation(cv, lambda c, s: puppet(c, s), n / fps, 8)`."""
    k = t * source_fps
    i = math.floor(k + 1e-9)
    w = k - i
    t0, t1 = i / source_fps, (i + 1) / source_fps
    if mode == 'hold' or w < 1e-6:
        draw_at(cv, t0)
    elif mode == 'blend':
        # Sum the two weighted frames in a group, then lay the sum over the
        # canvas: a true (1 - w)·A + w·B mix, opaque scene or sprite alike.
        c = cv.ctx
        c.save()
        c.push_group()
        with cv.layer(opacity=1 - w):
            draw_at(cv, t0)
        c.push_group()
        draw_at(cv, t1)
        c.pop_group_to_source()
        c.set_operator(cairo.OPERATOR_ADD)
        c.paint_with_alpha(w)
        c.set_operator(cairo.OPERATOR_OVER)
        c.pop_group_to_source()
        c.paint()
        c.restore()
    elif mode == 'motion':
        draw_at(cv, t)
    else:
        raise ValueError(f"frame_interpolation: mode must be 'hold', 'blend' or 'motion', not {mode!r}")


SOURCE_FPS = 5
LANES = (('hold', f'{SOURCE_FPS} fps source', demo.MUTED),
         ('blend', 'frame blending', demo.TEAL),
         ('motion', f'interpolated to {demo.FPS} fps', demo.ACCENT))
X0, X1 = 380, demo.W - 90


def _x(s):
    # Out and back across the lane once over the demo, easing at both ends.
    p = 0.5 - 0.5 * math.cos(2 * math.pi * vb.clamp01(s / demo.SECONDS))
    return X0 + (X1 - X0) * p


def draw(n, cv):
    t = n / demo.FPS
    label = demo.font(24, 700)
    for row, (mode, text, color) in enumerate(LANES):
        y = 120 + row * 150
        vb.text.draw(cv, [text], label, 60, y - 14, demo.INK if mode == 'motion' else demo.MUTED)
        cv.line(X0, y + 52, X1, y + 52, demo.LINE, width=2)
        for i in range(round(demo.SECONDS * SOURCE_FPS) + 1):  # where the source frames fall on the path
            xs = _x(i / SOURCE_FPS)
            cv.line(xs, y + 44, xs, y + 60, demo.MUTED, width=2, alpha=0.6)

        def ball(c, s, y=y, color=color):
            demo.dot(c, _x(s), y, 30, color=color)

        frame_interpolation(cv, ball, t, SOURCE_FPS, mode)
    cv.mark('ball', _x(t) - 30, 420 - 30, 60, 60)


CAPABILITY = Capability(
    id='frame-interpolation',
    name='Frame Interpolation',
    family='principles',
    group='Time remapping',
    aliases=('motion interpolation', 'frame blending', 'optical flow retiming', 'tweening frames',
             'frame rate up-conversion'),
    definition='New frames are generated between the existing ones so motion captured at a low '
               'frame rate plays back smoothly instead of jumping from pose to pose.',
    phrasings=('make this choppy animation play smooth',
               'fill in the missing frames so it is not jerky',
               'turn the 12 fps clip into buttery 60 fps',
               'smooth out the stutter between frames'),
    related=('interlace-combing', 'on-ones-on-twos-on-threes', 'smear-frame', 'isolines-contour-animation',
             'seamless-loop', 'morph-cut'),
    api=('videobuilder.capabilities.principles.frame_interpolation.frame_interpolation',),
    demo=lambda: demo.film(draw),
)
