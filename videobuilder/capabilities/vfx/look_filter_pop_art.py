"""Pop-art filter: one look of the Looks capability, built from videobuilder's own API, so this record
only names it and demos it with its worked example film, `examples/capabilities/look-filter-pop-
art.py` (an `Example` demo: see schema.py)."""
from ..schema import Capability, Example, Source

CAPABILITY = Capability(
    id='look-filter-pop-art',
    name='Pop-art filter',
    family='vfx',
    group='Filter looks',
    definition='Any picture in loud flat colour, comic dots and thick outlines.',
    description=('Restyles whatever the video draws -- a screenshot, a photo, footage: posterized to a '
                 'loud flat palette, every area screened with Ben-Day dots in a deeper shade of itself '
                 '(biggest in the shadows), every strong edge inked thick. The dots drift, so a held '
                 'screenshot crawls with them. For a hand-drawn comic panel instead, shade shapes with a '
                 'halftone dot fill under a thick ink outline, set the dot plate a couple of pixels off '
                 'from the ink like a misregistered print, and pop a jittering starburst with a short word '
                 'in it.'),
    phrasings=('Make my product demo pop art',
               'Give this a comic-book look, dot shading and thick outlines',
               'Add a jittering burst callout with a short word'),
    api=("with looks.filter(cv, 'pop-art', t): draw_as_usual(n, cv)",
         'videobuilder.halftone_pattern(pitch, radius, angle=.., color=..)  # a hand-drawn dot fill',
         'cv.arc(..., width=..)  # the thick outline',
         'videobuilder/looks/popart.py  # dot fills, outlines and the starburst, worked'),
    doc='skill/make-a-video/reference/looks.md',
    demo=Example('examples/capabilities/look-filter-pop-art.py'),
    old_ids=('comic-halftone',),
    source=Source('https://x.com/voxyz_ai/status/2109690569563746755',
                  '@Voxyz_ai',
                  upstream='https://github.com/alchaincyf/huashu-art-motion',
                  upstream_credit='@alchaincyf (huashu-art-motion, MIT)'),
)
