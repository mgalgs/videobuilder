"""Cross zoom: the camera rushes into the outgoing scene, smeared by a zoom
blur and washing out towards white, and at the peak of the rush the cut
lands on the incoming scene, which starts blown up and blurred and settles
back to its normal framing."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

RUSH_IN = vb.bezier(0.6, 0.0, 1.0, 0.7)    # accelerating into the outgoing scene
RUSH_OUT = vb.bezier(0.0, 0.3, 0.4, 1.0)   # decelerating out of the incoming one


def _zoomed(cv, scene, s, cx, cy, smear, echoes):
    """`scene(cv)` scaled by `s` about (cx, cy), with a zoom blur: `echoes`
    fading copies spread over a further `smear` of scale beyond `s`."""
    with cv.layer(dx=cx * (1 - s), dy=cy * (1 - s), scale=s):
        scene(cv)
    if smear <= 0 or echoes <= 0:
        return
    for i in range(1, echoes + 1):
        si = s * (1 + smear * i / echoes)
        with cv.layer(opacity=0.5 / (i + 1), dx=cx * (1 - si), dy=cy * (1 - si), scale=si):
            scene(cv)


def cross_zoom(cv, a, b, p, zoom=4.0, blur=0.35, echoes=6, flash=0.7, color='#ffffff', center=None):
    """Draw the cross zoom at progress `p` (0 -> 1). In the first half `a(cv)`
    scales from 1 up to `zoom` about `center` (default the frame centre),
    speeding up; in the second half `b(cv)` scales from `zoom` back down to 1,
    slowing down. The zoom blur (`echoes` copies over up to `blur` extra
    scale) and a wash of `color` (up to `flash` opacity) both peak at the cut.

    In a film, call it while two shots are live in an overlap, e.g.
    `cross_zoom(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    cx, cy = center if center is not None else (cv.width / 2, cv.height / 2)
    if p < 0.5:
        k = RUSH_IN(p / 0.5)
        scene, intensity = a, k
    else:
        k = 1 - RUSH_OUT((p - 0.5) / 0.5)
        scene, intensity = b, k
    s = 1 + (zoom - 1) * k
    _zoomed(cv, scene, s, cx, cy, blur * intensity, echoes)
    if flash > 0:
        cv.fill(color, alpha=flash * intensity ** 2)


CAPABILITY = Capability(
    id='cross-zoom',
    name='Cross zoom',
    family='transitions',
    group='Zoom',
    aliases=('zoom transition', 'zoom blur transition', 'cross zoom blur', 'zoom burst', 'punch-through zoom',
             'lens punch'),
    definition='The view lunges into the first shot in a streaking blur, and right at the fastest point '
               'it swaps to the second shot, which pulls back out of the same blur into place.',
    phrasings=('zoom into the first clip and come out of the zoom on the next one',
               'a fast blurry zoom that carries us from one scene to the next',
               'punch in on this shot and pull back out on the new one'),
    related=('cross-dissolve', 'infinite-zoom-tunnel', 'image-crossfade-slideshow', 'canvas-pan-and-zoom',
             'scale-zoom-through', 'zoom-through-shape'),
    api=('videobuilder.capabilities.transitions.cross_zoom.cross_zoom',
         'videobuilder.capabilities.transitions.zoom_blur.zoom_blur',
         'videobuilder.capabilities.transitions.zoom_through.zoom_through'),
    demo=lambda: demo.two_scenes(cross_zoom, start=1.4, length=1.0),
)
