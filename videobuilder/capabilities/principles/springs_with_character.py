"""Springs with character: built from videobuilder's own API, so this record only names it and demos it
with its worked example film, `examples/capabilities/springs-with-character.py` (an `Example` demo:
see schema.py)."""
from ..schema import Capability, Example, Source

CAPABILITY = Capability(
    id='springs-with-character',
    name='Springs with character',
    family='principles',
    group='Physics',
    category='Motion',
    order=2,
    definition='One spring, three damping ratios: firm to playful.',
    description=('The same spring drop at three damping ratios — 1.0 (no bounce), 0.6 (restrained) and 0.3 '
                 '(playful) — landing side by side so the difference in character is visible, not just '
                 'described.'),
    phrasings=('Drop this in with a playful spring, a bit of bounce',
               'Use a firm landing, no bounce',
               'Make it bouncier, more cartoonish'),
    api=('vb.spring_at(f, fps, **vb.damped(ratio, hz=2.0))',
         'vb.critical(stiffness)'),
    doc='skill/make-a-video/reference/motion.md',
    demo=Example('examples/capabilities/springs-with-character.py'),
    source=Source('https://x.com/flxrnc/status/2105311836190978392', '@flxrnc'),
)
