"""Eased entrances: built from videobuilder's own API, so this record only names it and demos it with
its worked example film, `examples/capabilities/eased-entrances.py` (an `Example` demo: see
schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='eased-entrances',
    name='Eased entrances',
    family='principles',
    group='Easing',
    category='Motion',
    order=1,
    definition='The named motion tokens, compared side by side.',
    description=("Five named easing curves — videobuilder's motion tokens — each sliding a chip into place "
                 'on its own row, so their character is easy to tell apart: a fast settle, a restrained '
                 'glide, a small overshoot.'),
    phrasings=('Ease this in fast, then let it settle gently',
               'Use a restrained entrance, nothing bouncy',
               'Make the exit quicker than the entrance, and a little brisker'),
    api=('vb.ease_out_expo',
         'vb.ease_out_quint',
         'vb.ease_in_out_quart',
         'vb.ease_out_back',
         'vb.ease_in_expo',
         'vb.interpolate(f, keys, values, ease=...)'),
    doc='skill/make-a-video/reference/motion.md',
    demo=Example('examples/capabilities/eased-entrances.py'),
)
