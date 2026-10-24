"""Image treatments: built from videobuilder's own API, so this record only names it and demos it with
its worked example film, `examples/capabilities/image-treatments.py` (an `Example` demo: see
schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='image-treatments',
    name='Image treatments',
    family='vfx',
    group='Blend & composite',
    category='Imagery and camera',
    order=3,
    definition='Cover and contain crops, rounded clips, soft shadows.',
    description=('The same generated image shown cover-cropped, contain-fitted, clipped to a rounded rect '
                 'and lifted with a soft shadow — the box-model moves for putting a picture in a layout.'),
    phrasings=('Cover-crop this image into the card',
               'Fit it contain, with rounded corners and a soft shadow',
               'Give this picture a drop shadow, like a card'),
    api=('Box.cover(w, h)',
         'Box.contain(w, h)',
         'cv.clip(x, y, w, h, radius=...)',
         'cv.shadow(...)'),
    doc='skill/make-a-video/reference/api.md',
    demo=Example('examples/capabilities/image-treatments.py'),
)
