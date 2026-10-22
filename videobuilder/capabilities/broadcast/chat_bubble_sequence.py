"""Chat bubble sequence: a conversation plays out as message bubbles that
pop in one at a time, alternating between the left and right speaker, each
growing out of its tail corner with a small overshoot."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def bubble_pops(t, arrivals, pop=0.35, ease=vb.ease_out_back):
    """How far each bubble has popped in at time `t` (seconds), for bubbles
    arriving at the times in `arrivals`: 0 before it arrives, then `ease`
    from 0 to 1 over `pop` seconds (the default overshoots a little)."""
    return [ease(vb.clamp01((t - a) / pop)) if t >= a else 0.0 for a in arrivals]


def draw_chat_bubble(cv, text, font, x, y, side, p, fill, ink, pad=(22, 12), radius=None, tail=12):
    """Draw one message bubble at pop progress `p` (0 -> 1, may overshoot).

    `side` is 'left' or 'right': a left bubble's left edge sits at `x`, a
    right bubble's right edge does; `y` is its top. The bubble grows from its
    bottom corner on that side, where a small tail points at the speaker,
    and fades in over the first part of the pop. Returns its Box."""
    px, py = pad
    tw, th = vb.text.block_size([text], font)
    w, h = tw + 2 * px, th + 2 * py
    radius = h * 0.4 if radius is None else radius
    left = x if side == 'left' else x - w
    if p <= 0:
        return vb.Box(left, y, w, h)
    ax = left if side == 'left' else left + w   # the corner it grows out of
    ay = y + h
    with cv.layer(opacity=vb.clamp01(p * 2.5), dx=ax, dy=ay, scale=max(p, 0.001)):
        bx, by = left - ax, y - ay
        cv.shadow(bx, by, w, h, radius=radius, dy=6, blur=18, color=(0, 0, 0, 0.35))
        cv.rect(bx, by, w, h, fill, radius=radius)
        c = cv.ctx   # the tail: a little wedge hanging off the speaker's bottom corner
        s = 1 if side == 'right' else -1
        c.move_to(-s * tail * 2.2, 0)
        c.line_to(s * tail * 0.7, tail * 0.6)
        c.line_to(0, -tail * 1.6)
        c.line_to(-s * tail * 2.2, -tail * 1.6)
        c.close_path()
        c.set_source_rgba(*vb.rgba(fill))
        c.fill()
        vb.text.draw(cv, [text], font, bx + px, by + py, ink)
    return vb.Box(left, y, w, h)


def draw_chat_sequence(cv, t, messages, arrivals, font, left, right, top, gap=16,
                       colors=('#2a2c33', demo.TEAL), inks=(demo.INK, demo.BG), first='left', **kw):
    """Draw a conversation at time `t`: `messages[i]` pops in at `arrivals[i]`
    seconds, speakers alternating starting from `first`. Left-side bubbles
    hang from x = `left`, right-side ones from x = `right`; rows stack down
    from `top`, `gap` apart, each row keeping its place before it arrives so
    nothing shifts. `colors` and `inks` are (left, right) bubble fill and
    text colour. `kw` goes to `bubble_pops`. Returns each bubble's Box."""
    boxes = []
    y = top
    for i, (text, p) in enumerate(zip(messages, bubble_pops(t, arrivals, **kw))):
        k = i % 2 if first == 'left' else 1 - i % 2
        side = ('left', 'right')[k]
        box = draw_chat_bubble(cv, text, font, left if side == 'left' else right, y, side, p, colors[k], inks[k])
        boxes.append(box)
        y += box.h + gap
    return boxes


MESSAGES = ('Are you still coming tonight?', 'Yes! Running a bit late', 'How late is late?',
            'Ten minutes, tops', 'Okay, saving you a seat', 'You are the best')


def draw(n, cv):
    t = n / demo.FPS
    arrivals = [0.15 + 0.45 * i for i in range(len(MESSAGES))]
    boxes = draw_chat_sequence(cv, t, MESSAGES, arrivals, demo.font(24, 600), left=200, right=demo.W - 200,
                               top=44)
    for box, a in zip(boxes, arrivals):
        if t >= a:
            cv.mark('bubble', *box)


CAPABILITY = Capability(
    id='chat-bubble-sequence',
    name='Chat bubble sequence',
    family='broadcast',
    group='Social media',
    aliases=('messaging sequence', 'text message reveal', 'chat conversation animation'),
    definition='A back-and-forth conversation builds up line by line, each message bubble springing '
               'into view from its speaker\'s side of the screen a beat after the previous one.',
    phrasings=('animate a text conversation with the bubbles appearing one by one',
               'show a chat where the messages pop in from left and right in turn',
               'a fake phone chat that plays out message by message'),
    related=('bouncing-dots', 'bubbles', 'circle-pop', 'staggered-cascade-reveal', 'jitter-and-boil-text',
             'like-heart-burst'),
    api=('videobuilder.capabilities.broadcast.chat_bubble_sequence.draw_chat_sequence',
         'videobuilder.capabilities.broadcast.chat_bubble_sequence.draw_chat_bubble',
         'videobuilder.capabilities.broadcast.chat_bubble_sequence.bubble_pops'),
    demo=lambda: demo.film(draw),
)
