"""Cut-out characters: a few drawn poses of one character, moved in code.

    fox = vb.Puppet({'idle': 'fox/idle.png', 'talk': 'fox/talk.png'}, height=380)
    pose, age = fox.pose_at(n, [(0, 'idle'), (12, 'talk'), (16, 'idle')])
    fox.draw(cv, pose, x, ground_y, sx=1.02, sy=0.98, mark='fox')
    g = fox.walk(n, step=7.5)       # a bounce-walk on the spot, two steps a beat at 120 bpm
    fox.draw(cv, 'idle', x, ground_y - g.lift, sx=g.sx, sy=g.sy, lean=g.lean)
"""
import math
from collections import namedtuple

import cairo
from PIL import Image as PILImage

from .canvas import Image
from .layout import Box

_OPAQUE = 128      # alpha at or above this counts as the character
_FEET_BAND = 0.06  # the lowest share of a pose's height whose middle is its feet


def _measure(pil):
    """(bbox, feet): the opaque bounding box (x0, y0, x1, y1) and the feet point
    (x, y) of a cut-out: the middle of its lowest opaque rows, on its lowest row."""
    alpha = pil.getchannel('A').point(lambda v: 255 if v >= _OPAQUE else 0)
    bbox = alpha.getbbox()
    if bbox is None or alpha.getextrema()[0] == 255:
        raise ValueError('a puppet pose must be a cut-out: a picture with a transparent background around the character')
    x0, y0, x1, y1 = bbox
    band = max(1, round((y1 - y0) * _FEET_BAND))
    fx0, _, fx1, _ = alpha.crop((x0, y1 - band, x1, y1)).getbbox()
    return bbox, (x0 + (fx0 + fx1) / 2, y1)


Gait = namedtuple('Gait', 'lift sx sy lean phase')
Gait.__doc__ = """One frame of `Puppet.walk`: `lift` px off the ground, `sx`/`sy` and
`lean` for `Puppet.draw`, and `phase`, 0..1 through the step (0 on contact)."""


class Puppet:
    """A character drawn from cut-out pictures (PNGs with a transparent
    background), one per pose, moved by transforms about its feet.

    `poses` maps a pose name to a path or a PIL image. Each picture is decoded
    and downscaled once, here, so the first pose's character (its opaque
    pixels, not the whole picture) stands `height` px tall; every pose shares
    that one factor, so poses drawn at the same size stay the same size.

    Each pose is placed by its own feet (the middle of its lowest opaque
    rows), so swapping poses whose pictures aren't registered alike doesn't
    make the character jump. Feet within `snap` source px of the first
    pose's are taken as the first pose's: poses that differ only at the
    mouth or eyes measure a pixel apart from antialiasing noise, and a
    talk flap shouldn't shimmer by that pixel."""

    def __init__(self, poses, height, snap=3):
        if not poses:
            raise ValueError('a puppet needs at least one pose')
        self.names = tuple(poses)
        pils = {}
        for name, src in poses.items():
            pil = src if isinstance(src, PILImage.Image) else PILImage.open(src)
            pils[name] = pil.convert('RGBA')
        measured = {name: _measure(pil) for name, pil in pils.items()}
        (_, y0, _, y1), ref_feet = measured[self.names[0]]
        self.factor = height / (y1 - y0)
        self._poses = {}
        for name, pil in pils.items():
            bbox, feet = measured[name]
            if abs(feet[0] - ref_feet[0]) <= snap and abs(feet[1] - ref_feet[1]) <= snap:
                feet = ref_feet
            k = self.factor
            w, h = max(1, round(pil.width * k)), max(1, round(pil.height * k))
            img = Image.from_pil(pil.resize((w, h), PILImage.LANCZOS))
            sx, sy = w / pil.width, h / pil.height
            fx, fy = feet[0] * sx, feet[1] * sy
            x0, y0, x1, y1 = bbox
            # Offsets from the feet, in drawn px: the picture's top left, and its opaque box.
            self._poses[name] = (img, (-fx, -fy), Box(x0 * sx - fx, y0 * sy - fy, (x1 - x0) * sx, (y1 - y0) * sy))
        self.height = height

    def box(self, pose):
        """The pose's opaque box relative to its feet, at rest (feet at 0, 0)."""
        return self._poses[pose][2]

    @staticmethod
    def pose_at(n, holds):
        """(pose, age): the pose held at frame `n` from `holds`, a list of
        (frame, pose) sorted by frame, each held until the next; and how many
        frames it has been held (0 on the frame it snaps in, for a pop).
        Before the first hold, the first pose, aged from frame 0."""
        pose, at = holds[0][1], 0
        for frame, name in holds:
            if frame > n:
                break
            pose, at = name, frame
        return pose, n - at

    def draw(self, cv, pose, x, y, sx=1.0, sy=1.0, angle=0.0, lean=0.0, scale=1.0, alpha=1.0, mark=None):
        """Draw `pose` with its feet at (x, y). About the feet: `sx`/`sy`
        squash and stretch, `lean` shears it (its top moves `lean` x its
        height sideways, feet planted), `angle` (radians) turns it, `scale`
        sizes it. `mark` names a `cv.mark` of its opaque box, transformed.
        Returns the marked Box, or None with no `mark`."""
        img, (ox, oy), box = self._poses[pose]
        c = cv.ctx
        c.save()
        c.translate(x, y)
        if angle:
            c.rotate(angle)
        if lean:
            c.transform(cairo.Matrix(1, 0, -lean, 1, 0, 0))   # x -= lean * y; y is negative up the body
        c.scale(sx * scale, sy * scale)
        cv.image(img, ox, oy, img.w, img.h, alpha=alpha)
        out = cv.mark(mark, *box) if mark else None
        c.restore()
        return out

    @staticmethod
    def breath(n, period, depth=0.012):
        """(sx, sy) for `draw` at frame `n` of a slow breath: the body rises
        `depth` taller and a third as much narrower, once every `period`
        frames. A whole number of periods across a loop keeps the seam clean."""
        s = math.sin(2 * math.pi * n / period)
        return 1 - depth / 3 * s, 1 + depth * s

    def walk(self, n, step, rise=0.035, squash=0.05, lean=0.04, start=0):
        """A Gait for frame `n` of a bounce-walk on the spot, the cut-out TV
        walk for a character with no leg drawings: one step every `step`
        frames from frame `start` (put steps on the beat: `step =
        GRID.frames_per_beat / 2` is two a beat). On each contact the body is
        down on the ground with a quick squash (`squash`: share wider and
        shorter); halfway through the step, on the passing position, it's up
        `rise` x its height. It leans forward `lean` the whole time, a little
        more as it comes down. Moving the ground and background past
        underneath at a steady speed is what makes it read as walking; a
        whole number of steps across a loop keeps the seam clean."""
        phase = ((n - start) / step) % 1.0
        up = math.sin(math.pi * phase)                           # 0 on contact, 1 passing; a sharp bounce off the ground
        contact = max(0.0, math.cos(2 * math.pi * phase)) ** 4   # a short pulse about each contact
        return Gait(lift=rise * self.height * up, sx=1 + squash * contact, sy=1 - squash * contact,
                    lean=lean * (1 + 0.35 * contact), phase=phase)
