"""Team color wipe: a broad slanted band in a team's colours -- a solid
field with pinstripes, trimmed with a stripe in the second colour and a
white hairline -- sweeps across the frame, and the team or player card is
left behind it as its tail clears."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

GOLD, NAVY, WHITE = '#f2b705', '#16306b', '#ffffff'


def _edge(x, slant, h, pad):
    """The slanted line through the bottom at `x`: (top point, bottom point),
    leaning right as it rises (`slant` is horizontal run per unit of height)."""
    return (x + slant * (h + 2 * pad), -pad), (x, h + pad)


def _clip_left_of(ctx, x, slant, h, pad):
    """Clip to everything left of the slanted edge at `x`."""
    (tx, ty), (bx, by) = _edge(x, slant, h, pad)
    far = -slant * (h + 2 * pad) - 4 * pad - abs(x)
    ctx.new_path()
    ctx.move_to(far, ty)
    ctx.line_to(tx, ty)
    ctx.line_to(bx, by)
    ctx.line_to(far, by)
    ctx.close_path()
    ctx.clip()


def team_color_wipe(cv, a, b, p, color=GOLD, trim=NAVY, edge=WHITE, slant=0.35, band=0.6, pinstripes=True,
                    ease=vb.ease_in_out_quart):
    """Draw the wipe at progress `p` (0 -> 1): `a(cv)`, a slanted band of
    the team's `color` crossing left to right over it, its leading edge
    trimmed with a `trim` stripe and an `edge` hairline, and `b(cv)` behind
    the band's tail (itself trimmed in `trim`). `band` is the band's length
    as a fraction of the sweep: near 0 the card follows right on the edge,
    near 1 the screen is all team colour mid-way. `slant` is how far the
    edges lean (horizontal per vertical); `pinstripes` lays faint diagonal
    lines over the colour field.

    In a film, call it over a two-shot overlap, e.g. into a player card:
    `team_color_wipe(cv, lambda c: scene_a(c, old), lambda c: player_card(c, new), new.f / overlap_frames,
    color=team.primary, trim=team.secondary)`."""
    w, h = cv.width, cv.height
    pad = 40
    p = vb.clamp01(p)
    gap = vb.clamp01(band) * 0.5
    lead_q = ease(vb.clamp01(p / (1 - gap)))
    tail_q = ease(vb.clamp01((p - gap) / (1 - gap)))
    start = -slant * (h + 2 * pad) - pad - 120   # the whole band, trims included, starts off the left side
    end = w + pad + 120                          # and the tail ends past the right one
    lead = start + (end - start) * lead_q
    tail = start + (end - start) * tail_q

    a(cv)
    if lead_q <= 0:
        return
    ctx = cv.ctx
    r, g, bl = _rgb(color)
    ctx.save()
    _clip_left_of(ctx, lead, slant, h, pad)
    ctx.set_source_rgb(r, g, bl)
    ctx.paint()
    if pinstripes:   # faint darker lines parallel to the edges, fixed to the frame so they don't crawl
        ctx.set_source_rgba(r * 0.9, g * 0.9, bl * 0.9, 1.0)
        step = 40
        x = -slant * (h + 2 * pad) - step
        while x < w + step:
            _strip_path(ctx, x, 9, slant, h, pad)
            ctx.fill()
            x += step
    _strip_path(ctx, lead - 12, 26, slant, h, pad)   # trim stripe just behind the leading edge
    ctx.set_source_rgb(*_rgb(trim))
    ctx.fill()
    _strip_path(ctx, lead, 6, slant, h, pad)        # the white hairline on the very edge
    ctx.set_source_rgb(*_rgb(edge))
    ctx.fill()
    ctx.restore()

    if tail_q <= 0:
        return
    ctx.save()
    _clip_left_of(ctx, tail, slant, h, pad)
    b(cv)
    ctx.restore()
    if tail_q < 1:
        ctx.save()
        _strip_path(ctx, tail + 10, 10, slant, h, pad)   # a thin trim line rides the tail too
        ctx.set_source_rgb(*_rgb(trim))
        ctx.fill()
        ctx.restore()


def _strip_path(ctx, x, width, slant, h, pad):
    """Path a slanted parallelogram from `x - width` to `x` along the bottom."""
    (tx, ty), (bx, by) = _edge(x, slant, h, pad)
    ctx.new_path()
    ctx.move_to(tx - width, ty)
    ctx.line_to(tx, ty)
    ctx.line_to(bx, by)
    ctx.line_to(bx - width, by)
    ctx.close_path()


def _rgb(hex_color):
    """'#rrggbb' as cairo's (r, g, b) in 0..1."""
    s = hex_color.lstrip('#')
    return tuple(int(s[i:i + 2], 16) / 255 for i in (0, 2, 4))


def player_card(cv, name='R. OKAFOR', number='23', team='WOLVES', color=GOLD, trim=NAVY):
    """A simple player card in the team's colours: a `trim` field, a `color`
    panel with the shirt number, the team and player name beside it."""
    W, H = cv.width, cv.height
    cv.fill(trim)
    cv.rect(0, H * 0.88, W, H * 0.12, color, alpha=0.95)
    s = H * 0.42                 # the number panel's side
    x0, y0 = W * 0.1, H * 0.44 - s / 2
    cv.shadow(x0, y0, s, s, radius=s * 0.07, dy=8, blur=24, color=(0, 0, 0, 0.45))
    cv.rect(x0, y0, s, s, color, radius=s * 0.07)
    demo.word(cv, number, x0 + s / 2, y0 + s / 2, size=round(s * 0.62), color=trim, weight=900)
    tx = x0 + s + H * 0.08
    vb.text.draw(cv, [team], demo.font(round(H * 0.055), 800), tx, y0 + s * 0.2, color)
    vb.text.draw(cv, [name], demo.font(round(H * 0.11), 900), tx, y0 + s * 0.36, WHITE)
    cv.rect(tx, y0 + s * 0.74, s * 0.95, H * 0.012, color, radius=H * 0.006)


CAPABILITY = Capability(
    id='team-color-wipe',
    name='Team color wipe',
    family='broadcast',
    group='Sports graphics',
    aliases=('team color sweep', 'team banner wipe'),
    definition='A wide slanted band in a team\'s colours, edged with a contrasting stripe, '
               'races across the screen and leaves that team\'s player or line-up card behind it.',
    phrasings=('sweep the team colours across the screen into the player card',
               'a big diagonal stripe in the club colours wipes to the line-up',
               'brand the transition into the team graphic with their colours'),
    related=('fill-sweep-button', 'clock-wipe', 'paint-brush-wipe', 'shape-fill-sweep',
             'gradient-sweep-across-text', 'gradient-wipe'),
    api=('videobuilder.capabilities.broadcast.team_color_wipe.team_color_wipe',
         'videobuilder.capabilities.broadcast.team_color_wipe.player_card'),
    demo=lambda: demo.two_scenes(team_color_wipe, start=1.0, length=1.6, b=player_card),
)
