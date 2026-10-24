"""Camera on a screenshot: built from videobuilder's own API, so this record only names it and demos it
with its worked example film, `examples/capabilities/camera-on-a-screenshot.py` (an `Example` demo:
see schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='camera-on-a-screenshot',
    name='Camera on a screenshot',
    family='camera',
    group='Camera moves',
    category='Imagery and camera',
    order=1,
    definition='A window pans and zooms across a captured screen.',
    description=('A camera window pans and zooms across a (generated) screenshot, with a navbar strip '
                 'pinned to the top of the window while the page itself scrolls underneath it.'),
    phrasings=('Pan and zoom across this screenshot, pin the navbar',
               'Push in on the pricing table, then pan down',
               'Keep the header pinned while the camera scrolls the page'),
    api=('cv.view(img, box, center=, scale=, radius=)',
         'vb.log_lerp(a, b, p)  # even zoom',
         'view.pin(src, y=box.y)'),
    doc='skill/make-a-video/reference/api.md',
    demo=Example('examples/capabilities/camera-on-a-screenshot.py'),
    poster=0,  # the full-dashboard frame
)
