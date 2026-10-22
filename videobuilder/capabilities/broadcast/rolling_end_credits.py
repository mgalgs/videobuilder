"""Rolling end credits: a long column of roles and names crawls up the frame
at a steady speed, entering at the foot and leaving at the head, softened by
a fade at both edges. Roles sit right-aligned beside a centre gutter, names
left-aligned after it; headings and lone names are centred.

`compendium/components/ending_credits_roll.py` is a finished ending card that
eases to a stop on a closing line; `rolling_credits` is the plain steady roll
under it, for a film to drive with its own credits and pace."""
import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def rolling_credits(cv, credits, scroll, role_font=None, name_font=None, heading_font=None, cx=None, gutter=14,
                    gap=14, section=34, role_color=demo.MUTED, name_color=demo.INK, heading_color=demo.ACCENT,
                    fade=60):
    """Draw the credits column scrolled up by `scroll` pixels.

    `credits` is a sequence of `(role, name)` pairs: both set gives a
    two-column row, the role to the left of the gutter at `cx` and the name
    to its right; a name alone is centred; a role alone with an empty
    name is a centred section heading, with extra space above it. At
    `scroll=0` the column's top sits on the frame's bottom edge; a steady roll
    is `scroll = speed * seconds`. The top and bottom `fade` pixels of the
    frame fade the column out. Returns the column's height, so the roll is
    done once `scroll >= height + cv.height`."""
    role_font = role_font or demo.mono(15, 600, tracking=0.12)
    name_font = name_font or demo.font(26, 650)
    heading_font = heading_font or demo.mono(17, 700, tracking=0.2)
    cx = cv.width / 2 if cx is None else cx
    H = cv.height
    rows, y = [], 0.0
    for i, (role, name) in enumerate(credits):
        if role and not name:
            if i:
                y += section
            rows.append((y, 'heading', role.upper()))
            y += vb.text.line_height(heading_font) + gap
        else:
            rows.append((y, 'row' if role else 'name', (role.upper(), name)))
            y += vb.text.line_height(name_font) + gap
    height = y - gap if rows else 0.0

    top = H - scroll
    ctx = cv.ctx
    ctx.push_group()
    nh = vb.text.line_height(name_font)
    for ry, kind, what in rows:
        ty = top + ry
        if ty > H or ty + nh < 0:
            continue
        if kind == 'heading':
            w = vb.text.measure(what, heading_font)
            vb.text.draw(cv, [what], heading_font, cx - w / 2, ty, heading_color)
        elif kind == 'name':
            w = vb.text.measure(what[1], name_font)
            vb.text.draw(cv, [what[1]], name_font, cx - w / 2, ty, name_color)
        else:
            role, name = what
            rw = vb.text.measure(role, role_font)
            dy = (nh - vb.text.line_height(role_font)) / 2
            vb.text.draw(cv, [role], role_font, cx - gutter - rw, ty + dy, role_color)
            vb.text.draw(cv, [name], name_font, cx + gutter, ty, name_color)
    ctx.pop_group_to_source()
    if fade > 0:
        f = min(0.5, fade / H)
        mask = cairo.LinearGradient(0, 0, 0, H)
        mask.add_color_stop_rgba(0, 0, 0, 0, 0)
        mask.add_color_stop_rgba(f, 0, 0, 0, 1)
        mask.add_color_stop_rgba(1 - f, 0, 0, 0, 1)
        mask.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.mask(mask)
    else:
        ctx.paint()
    return height


CREDITS = (
    ('Cast', ''),
    ('The Keeper', 'Ada Fennimore'), ('The Stranger', 'Joss Okafor'), ('The Child', 'Marlo Vance'),
    ('Ferryman', 'Teodor Brask'), ('Night Clerk', 'Ines Calloway'),
    ('Crew', ''),
    ('Director', 'Priya Lindqvist'), ('Writer', 'Wren Halloway'), ('Producer', 'Mateo Arkwright'),
    ('Cinematography', 'Suki Ondaatje'), ('Editor', 'Felix Marchetti'), ('Sound', 'Noor Haddad'),
    ('Music', 'The Low Tide Trio'), ('Colour', 'Elsie Varga'), ('Gaffer', 'Rufus Penhaligon'),
    ('Special thanks', ''),
    ('', 'Everyone at the lighthouse'), ('', 'The town of Port Ellery'),
)

SPEED = 300  # px per second, steady


def draw(n, cv):
    rolling_credits(cv, CREDITS, demo.H * 0.55 + SPEED * n / demo.FPS)


CAPABILITY = Capability(
    id='rolling-end-credits',
    name='Rolling end credits',
    family='broadcast',
    group='End cards',
    aliases=('credit roll', 'end crawl', 'scrolling credits', 'closing credits', 'roller credits'),
    definition='A tall list of roles and names glides steadily up the screen from bottom to top, '
               'the way the closing credits of a film run.',
    phrasings=('scroll the credits up the screen like at the end of a movie',
               'roll the names of everyone who worked on it at the end',
               'a slow upward crawl of cast and crew names'),
    related=('roll-up', 'horizontal-scroll-section', 'timeline-scroll', 'scrollytelling-step-sequence',
             'scroll-driven-text-reveal', 'scrolling-led-marquee-text'),
    api=('videobuilder.capabilities.broadcast.rolling_end_credits.rolling_credits',
         'videobuilder.compendium.components.ending_credits_roll.COMPONENT'),
    demo=lambda: demo.film(draw),
)
