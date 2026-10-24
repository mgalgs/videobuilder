"""Gradient Wipe: the same idea as Luma Wipe (`luma_wipe.py`, which keeps the
capability) -- both reveal the incoming scene through a greyscale map,
darkest areas first and lightest last, with a feathered edge between the two
scenes. This module's own code stays (a film may still import it), but it is
no longer a capability of its own."""
import math
from functools import lru_cache

from PIL import Image as PILImage

from ...canvas import _a8

MERGED_INTO = 'luma-wipe'

_MAP = (192, 108)  # maps are built small and smooth, then stretched to the frame


@lru_cache(maxsize=16)
def linear_map(angle=0.0):
    """A straight ramp, dark where the wipe starts: `angle` in degrees, 0 runs
    left to right, 90 top to bottom. Returns a small 'L' PIL image."""
    return _build(lambda u, v: u * math.cos(math.radians(angle)) + v * math.sin(math.radians(angle)))


@lru_cache(maxsize=16)
def radial_map(cx=0.5, cy=0.5):
    """Dark at (cx, cy) (fractions of the frame), lighter outward: an iris
    opening from that point."""
    return _build(lambda u, v: math.hypot((u - cx) * 16 / 9, v - cy))


@lru_cache(maxsize=16)
def wave_map(angle=0.0, waves=1.5, depth=0.12):
    """A ramp like `linear_map` whose edge ripples `waves` times across the
    frame, `depth` of the frame deep: a liquid, curving front."""
    a = math.radians(angle)
    c, s = math.cos(a), math.sin(a)
    return _build(lambda u, v: u * c + v * s + depth * math.sin(2 * math.pi * waves * (v * c - u * s)))


def _build(f):
    """Sample f(u, v) over the unit frame and normalise it to 0..255."""
    w, h = _MAP
    vals = [f((x + 0.5) / w, (y + 0.5) / h) for y in range(h) for x in range(w)]
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1.0
    img = PILImage.new('L', _MAP)
    img.putdata([round(255 * (v - lo) / span) for v in vals])
    return img


def gradient_wipe(cv, a, b, p, softness=0.2, map=None):
    """Draw the wipe at progress `p` (0 -> 1): `a(cv)` everywhere, then
    `b(cv)` over it wherever the grayscale `map` is darker than the moving
    threshold, fading in across a band `softness` wide (0..1 of the map's
    range; near 0 is a hard edge). `map` is any 'L' PIL image, stretched to
    the frame, dark revealing first; default `wave_map()`. Use `linear_map`,
    `radial_map` or your own (a logo, noise, a photo's luminance).

    In a film, call it while two shots are live in an overlap, e.g.
    `gradient_wipe(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    a(cv)
    if p <= 0:
        return
    s = max(softness, 1 / 255)
    t = p * (1 + s)  # the threshold runs from 0 to past the lightest value, so p=1 shows all of b
    lut = [round(255 * min(1.0, max(0.0, (t - g / 255) / s))) for g in range(256)]
    sw, sh = cv.surface.get_width(), cv.surface.get_height()
    src = map if map is not None else wave_map()
    mask = _a8(src.convert('L').resize((sw, sh), PILImage.BILINEAR).point(lut))
    c = cv.ctx
    c.save()
    c.push_group()
    b(cv)
    c.pop_group_to_source()   # the source keeps the user space it was drawn in
    c.identity_matrix()       # the mask is in device pixels
    c.mask_surface(mask, 0, 0)
    c.restore()


def _demo_wipe(cv, a, b, p):
    # a gentle sine ease keeps the soft front on screen for most of the wipe
    gradient_wipe(cv, a, b, 0.5 - 0.5 * math.cos(math.pi * p))
