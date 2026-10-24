"""Looks: built from videobuilder's own API, so this record only names it and demos it with its worked
example film, `examples/capabilities/looks.py` (an `Example` demo: see schema.py)."""
from ..schema import Capability, Example, MemberBrief, Members, Source

# What a creator's new member ships, and how its builder is briefed (community.brief).
LOOKS_MEMBER = MemberBrief(
    file='look.py',
    registry='videobuilder.looks',
    intro=(("Add a new look to videobuilder's Looks family: a creator saw an art style and wants any video "
            'to be able to ask for it by name, the way it asks for "pop art" or "woodblock" today. Make '
            'one reusable look that paints any scene, not one picture in that style.'),
           ('Read skill/make-a-video/reference/looks.md first: it gives the look contract, and the '
            'built-in looks (the videobuilder.looks package, one module each) are worked examples of it.')),
    code=('ONE look following that contract: `paint(cv, scene, t, age)` paints a whole '
          '`videobuilder.looks.Scene` (every pixel of scene.w by scene.h) from the roles of its regions '
          '(sky, water, land, building, figure, light), its sun, beacon and stars -- whatever scene a '
          'video gives it, in any frame shape -- and `LOOK = looks.Look(name, title, line, paint)`, with '
          "`name` equal to capability.toml's id. Give it one signature motion that moves across a good "
          'part of the frame. Draw everything in code with videobuilder: never copy the attached '
          "{source}'s artwork, images, text or branding, and never name an artist in it."),
    film=("a 3 to 6 second demo that imports look.py from beside itself (put the file's own directory on "
          "sys.path) and paints `looks.lighthouse(w, h, t)` with it -- the scene every look's demo shares, "
          'so they compare -- in one 720x720 format, with a small plaque naming the look. It must pass the '
          'motion floor: `looks.motion_floor(FILM, start, end)` of at least `looks.FLOOR` over the part '
          'where the look holds; check it before you finish.'),
    doc='a short reference doc: how the look paints each role, what moves, and its options.',
)

CAPABILITY = Capability(
    id='looks',
    name='Looks',
    family='vfx',
    group='Looks',
    category='Looks',
    order=1,
    definition='Named art styles any video can ask for by name, each moving its own way.',
    description=('Named art styles any video can ask for by name ("make it pop art", "try a few looks"), '
                 'each with its own signature motion, in two kinds. A scene look repaints a picture the '
                 'video describes as a few shapes with roles (sky, water, land, buildings, figures, '
                 'lights, the sun and a beacon); a filter look restyles whatever the video draws -- a '
                 'photo, a screen capture, footage -- every pixel, frame by frame. They share names where '
                 'the style carries over, so "pop art" finds both. Creators can add scene looks of their '
                 'own.'),
    phrasings=('Make it look like pop art',
               'Try a few different looks on this and let me pick',
               'Make my product demo look like an 8-bit game',
               'Give it a dreamy surreal look, things melting'),
    api=('looks.Scene(w, h, [looks.Region(role, points), ...], horizon=, sun=(x, y, r), beacon=(x, y))',
         "looks.paint(cv, 'pop-art', scene, t, age)  # a scene look",
         'looks.names() / looks.get(name)',
         "with looks.filter(cv, 'pop-art', t): draw_as_usual(n, cv)  # a filter look, on any picture",
         'looks.filters() / looks.get_filter(name)',
         'looks.relay(cv, scene, t, names, hold=2.0)  # try several in turn',
         'looks.motion_floor(film, start, end) >= looks.FLOOR'),
    doc='skill/make-a-video/reference/looks.md',
    demo=Example('examples/capabilities/looks.py'),
    poster=5 * 24 + 12,  # mid-hold on pop art, not mid-wipe
    members=Members(
        ids=('look-swirl',
             'look-pointillism',
             'look-woodblock',
             'look-melt',
             'look-bauhaus',
             'look-pop-art',
             'look-pixel',
             'look-blueprint',
             'paper-collage',
             'look-filter-pop-art',
             'look-filter-pixel',
             'look-filter-woodblock',
             'look-filter-blueprint',
             'look-filter-pointillism'),
        noun=('look', 'looks'),
        lead='Try a few looks',
        lead_line='Several in turn, wiping from one to the next.',
        kinds=(('scene', 'Scene looks', 'for a picture the video draws: it describes the shapes, the look paints them'),
               ('filter', 'Filter looks', 'for any picture: a photo, a screen capture, footage, every pixel restyled')),
        names={'look-swirl': 'swirl',
               'look-pointillism': 'pointillism',
               'look-woodblock': 'woodblock',
               'look-melt': 'melt',
               'look-bauhaus': 'bauhaus',
               'look-pop-art': 'pop-art',
               'look-pixel': 'pixel',
               'look-blueprint': 'blueprint',
               'look-filter-pop-art': 'pop-art',
               'look-filter-pixel': 'pixel',
               'look-filter-woodblock': 'woodblock',
               'look-filter-blueprint': 'blueprint',
               'look-filter-pointillism': 'pointillism'},
        brief=LOOKS_MEMBER),
    source=Source('https://x.com/voxyz_ai/status/2109690569563746755',
                  '@Voxyz_ai',
                  upstream='https://github.com/alchaincyf/huashu-art-motion',
                  upstream_credit='@alchaincyf (huashu-art-motion, MIT)'),
)
