"""Type: built from videobuilder's own API, so this record only names it and demos it with its worked
example film, `examples/capabilities/type.py` (an `Example` demo: see schema.py)."""
from ..schema import Capability, Example, MemberBrief, Members

# What a creator's new member ships, and how its builder is briefed (community.brief).
TYPE_MEMBER = MemberBrief(
    file='style.py',
    registry='videobuilder.type',
    intro=(("Add a new type style to videobuilder's Type family: a creator saw a typography effect and "
            'wants any video to be able to ask for it by name, the way it asks for "split-flap" or '
            '"typewriter" today. Make one reusable style that sets any few lines, not one title in that '
            'style.'),
           ('Read skill/make-a-video/reference/type.md first: it gives the style contract, and the '
            'built-in styles (the videobuilder.type package, one module each) are worked examples of it.')),
    code=('ONE style following that contract: `draw(cv, p, t, box, clock)` sets `p.lines` (1 to 4 short '
          'lines, as given) in `p.ink` with `p.accent`, on `p.paper` or over whatever is already drawn '
          'when it is None, inside `box` in any frame shape, entering, holding (still moving) and leaving '
          'within `p.length` seconds (`clock.hold` and `clock.exit` say when) -- and `STYLE = '
          "vb.type.Style(name, title, line, draw)`, with `name` equal to capability.toml's id. Mark each "
          "line with `cv.mark('line-<i>', ...)` once it can be read, inside the box. Draw everything in "
          "code with videobuilder: never copy the attached {source}'s artwork, text or branding."),
    film=("a 5 to 6 second demo that imports style.py from beside itself (put the file's own directory on "
          'sys.path), registers it (`vb.type.register(STYLE)`) and plays it with `vb.type.film(name, '
          'props)` on three short lines of your own, in one 720x720 format. It must pass the motion floor: '
          '`vb.type.motion_floor(FILM, start, end)` of at least `vb.type.FLOOR` over the part where the '
          'style holds; check it before you finish.'),
    doc=('a short reference doc: what the style is for, how it enters, holds and leaves, and how it lays '
         'out tall, wide and square.'),
)

CAPABILITY = Capability(
    id='type',
    name='Type',
    family='typography',
    group='Type styles',
    category='Type',
    order=1,
    definition='Named typography styles any video can ask for by name, every one taking the same few props.',
    description=('Type-only moments asked for by name ("make the title a split-flap board", "type it on '
                 'like a terminal", "make the letters bounce"): each style is a short typography film of '
                 'its own -- the letters enter, hold while still moving, and leave -- drawn from the same '
                 'props every style takes: one to four short lines, three colours (ink, paper, accent) and '
                 'a length, 6 s inside a film or up to 18 s as a film of its own. Each lays itself out for '
                 'tall, wide and square frames, can run in a box or over another picture, and the ones '
                 'with an obvious sound (flap clicks, key strikes, a soft pop) bring it when asked.'),
    phrasings=('Make the title a split-flap departures board',
               'Type the headline on like a terminal, with a prompt',
               'Make the slogan bounce in, letters on springs',
               'Show me the same title in a few type styles'),
    api=("TITLE = vb.type.props(lines=['Gate 14', 'Now boarding'], ink=, paper=, accent=, length=6)",
         "vb.type.draw(cv, 'split-flap', TITLE, t)  # t: seconds since the style started",
         ("vb.type.draw(cv, 'rubber', vb.type.props(TITLE, paper=None), t, box=(x, y, w, h))  # over a "
          'picture'),
         "vb.type.film('typewriter', TITLE, length=18)  # one style as a film of its own",
         'vb.type.sounds(name, vb.type.props(TITLE, sound=True), at=frame)  # its clicks, keys or pops',
         'vb.type.props(TITLE, texture=False)  # a plain ground: no paper grain or scanlines',
         'vb.type.names() / vb.type.get(name)',
         'vb.type.relay(cv, names, TITLE, t, each=3.0)',
         'vb.type.motion_floor(film, start, end) >= vb.type.FLOOR'),
    doc='skill/make-a-video/reference/type.md',
    demo=Example('examples/capabilities/type.py'),
    poster=round(0.6 * 90),  # mid-hold on the split-flap board
    members=Members(
        ids=('type-split-flap',
             'type-typewriter',
             'type-terminal',
             'type-rubber',
             'type-rack-focus',
             'type-letter-cloud',
             'type-editorial'),
        noun=('type style', 'type styles'),
        lead='A few type styles',
        lead_line='The same three lines, one style after another.',
        names={'type-split-flap': 'split-flap',
               'type-typewriter': 'typewriter',
               'type-terminal': 'terminal',
               'type-rubber': 'rubber',
               'type-rack-focus': 'rack-focus',
               'type-letter-cloud': 'letter-cloud',
               'type-editorial': 'editorial'},
        brief=TYPE_MEMBER),
)
