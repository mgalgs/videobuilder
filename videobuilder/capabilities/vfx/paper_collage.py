"""Paper collage: one look of the Looks capability, built from videobuilder's own API, so this record
only names it and demos it with its worked example film, `examples/capabilities/paper-collage.py`
(an `Example` demo: see schema.py)."""
from ..schema import Capability, Example, Source

CAPABILITY = Capability(
    id='paper-collage',
    name='Paper collage',
    family='vfx',
    group='Scene looks',
    definition='Torn-paper headlines, cut-paper objects, a stamp, and a rip-open transition.',
    description=('The editorial paper-cutout explainer look: a grey-beige paper wall under still window '
                 'light, a headline printed on a torn scrap, a cut-paper object whose soft shadow follows '
                 'its outline, hand-drawn marks and a red rubber stamp, all moving in stop-motion steps -- '
                 'then the wall rips open from the middle, its flaps curling back to reveal one accent '
                 'colour with the next scene pasted on it. Objects are drawn shapes or images you supply, '
                 'never generated.'),
    phrasings=('Make this look like a paper collage explainer, all torn paper and cut-outs',
               'Put each headline on a torn strip of paper',
               'Rip the paper open to get to the next scene',
               'Stamp NO PROOF across it in red',
               'Make the paper pieces move like stop-motion, a bit choppy'),
    api=('paths.torn(outline, seed, amount=5)  # a torn edge, baked once at import',
         'cv.shape_shadow(points, dx=.., dy=.., blur=..)  # a lift shadow that follows the shape',
         'vb.paper_grain(w, h, seed)  # with cairo.OPERATOR_SOFT_LIGHT',
         'stepped_n = n - n % 2  # paper held on twos',
         'videobuilder.capabilities.shapes.collage_assembly.draw_collage(cv, pieces, p)'
         '  # the slide-in-and-press build order',
         'videobuilder.capabilities.shapes.cut_out_paper_animation.paper_piece(cv, points, color)'
         '  # the jerky hand-moved stepping',
         'videobuilder.capabilities.shapes.cut_out_paper_animation.held(n)'),
    doc='skill/make-a-video/reference/api.md',
    demo=Example('examples/capabilities/paper-collage.py'),
    poster=78,  # mid-rip, flaps curling back
    source=Source('https://x.com/OriSilver/status/2074089635177746707', '@OriSilver'),
)
