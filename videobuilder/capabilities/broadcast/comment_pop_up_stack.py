"""Comment Pop-up Stack: viewer comments turn up one after another in a
column, each fading in as it rises a short way into the next free slot
beneath the ones already posted, the way a live chat fills up."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def comment_stack(t, arrivals, pop=0.45, keep=None, ease=vb.ease_out_quint):
    """Where each comment is at time `t` (seconds), for comments posted at the
    times in `arrivals` (ascending). One `(enter, slot)` per comment: `enter`
    runs 0 -> 1 over `pop` seconds once it is posted (0 before), `slot` is
    its row in the column counting from the top. With `keep` set, the column
    holds at most that many: each later arrival scrolls it up one row, easing
    over `pop` seconds, so `slot` goes fractional and then negative as the
    oldest ones leave."""
    shift = 0.0
    if keep is not None:
        shift = sum(ease(vb.clamp01((t - a) / pop)) for a in arrivals[keep:])
    return [(ease(vb.clamp01((t - a) / pop)) if t >= a else 0.0, i - shift) for i, a in enumerate(arrivals)]


def draw_comment(cv, comment, x, y, w, h, panel='#20232b', edge=demo.LINE, ink=demo.INK):
    """One comment bubble at top-left (x, y): a rounded panel with a round
    avatar showing the poster's initial, their name in bold and the message
    below. `comment` is `(name, text, color)`, the colour filling the avatar."""
    name, text, color = comment
    r = min(14.0, h / 2)
    cv.shadow(x, y, w, h, radius=r, dy=6, blur=18, color=(0, 0, 0, 0.45))
    cv.rect(x, y, w, h, panel, radius=r)
    cv.outline(x, y, w, h, edge, width=2, radius=r)
    ar = h * 0.2
    ax, ay = x + h * 0.2 + ar, y + h * 0.18 + ar
    cv.sector(ax, ay, ar, 0, 2 * math.pi, color)
    demo.word(cv, name[:1].upper(), ax, ay, size=round(ar * 1.0), color=demo.BG, weight=800)
    nf = demo.font(round(h * 0.24), 800)
    _, nh = vb.text.block_size([name], nf)
    vb.text.draw(cv, [name], nf, ax + ar + h * 0.14, ay - nh / 2, ink)
    tf = demo.font(round(h * 0.25), 500)
    vb.text.draw(cv, [text], tf, x + h * 0.2, y + h * 0.55, ink)
    cv.mark('comment', x, y, w, h)


def draw_comment_stack(cv, t, comments, arrivals, x, top, w, h, gap=16, rise=24, pop=0.45, keep=None,
                       draw=draw_comment):
    """Draw `comments` posting at the times in `arrivals` as a column of
    `w` x `h` bubbles whose first row's top-left is (`x`, `top`), rows
    `h + gap` apart. Each arrival fades in while rising `rise` px and growing
    slightly into its row; with `keep`, older ones scroll up and fade out of
    the top. `draw(cv, comment, x, y, w, h)` draws one bubble (default
    `draw_comment`). Returns the Box of the rows in use."""
    used = 0
    for comment, (enter, slot) in zip(comments, comment_stack(t, arrivals, pop=pop, keep=keep)):
        alpha = enter * vb.clamp01(1 + slot)
        if alpha <= 0:
            continue
        used = max(used, slot + 1)
        y = top + slot * (h + gap)
        s = 0.94 + 0.06 * enter
        cx, cy = x + w / 2, y + h / 2
        with cv.layer(opacity=alpha, dx=cx * (1 - s), dy=cy * (1 - s) + rise * (1 - enter), scale=s):
            draw(cv, comment, x, y, w, h)
    return vb.Box(x, top, w, max(0.0, used * (h + gap) - gap))


COMMENTS = (('Maya', 'That timing is so satisfying.', '#f2b632'),
            ('Theo', 'Rewatched the ending twice!', demo.TEAL),
            ('Priya', 'How did you make the bounce?', '#8b8cf0'),
            ('Jonas', 'Saving this one for later.', demo.ACCENT))
ARRIVALS = (0.2, 0.8, 1.4, 2.0)


def draw(n, cv):
    w, h, gap = 500, 80, 16
    top = (demo.H - (len(COMMENTS) * (h + gap) - gap)) / 2
    draw_comment_stack(cv, n / demo.FPS, COMMENTS, ARRIVALS, (demo.W - w) / 2, top, w, h, gap=gap)


CAPABILITY = Capability(
    id='comment-pop-up-stack',
    name='Comment pop-up stack',
    family='broadcast',
    group='Social media',
    aliases=('comment bubble stream', 'reply stack', 'live chat feed', 'comment feed'),
    definition='Viewer comments, each a little card with an avatar, a name and a line of text, '
               'fade and float up into place one below another until they fill a column.',
    phrasings=('make the comments pop in one by one like a live chat',
               'show a few audience replies stacking up under each other',
               'social media comments appearing in a list, each sliding up into place'),
    related=('bouncing-dots', 'circle-pop', 'toast-slide-in-stack', 'stacked-line-build', 'avatar-stack-spread',
             'shape-stacking-drop'),
    api=('videobuilder.capabilities.broadcast.comment_pop_up_stack.draw_comment_stack',
         'videobuilder.capabilities.broadcast.comment_pop_up_stack.comment_stack',
         'videobuilder.capabilities.broadcast.comment_pop_up_stack.draw_comment'),
    demo=lambda: demo.film(draw),
)
