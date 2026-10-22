"""Drop Shadow Lift: text rises off the surface it sits on, and its shadow
falls further behind it, spreading and softening, so the words seem to float."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ...type import kit as type_kit

PAPER = '#e9e6df'


def lift_shadow(p, rise=22, dy=(3, 34), blur=(2, 20), alpha=(0.55, 0.28), scale=(1.0, 1.04)):
    """The lift at progress `p` (0 resting, 1 fully raised; values past 1
    from an overshooting ease carry on) as a dict: `rise`, how far the text
    moves up; `dy`, `blur` and `alpha`, its shadow's drop, softness and
    strength, each running from its pair's first value to its second; and
    `scale`, the text's growth about its centre as it comes nearer."""
    lerp = lambda ab: ab[0] + (ab[1] - ab[0]) * p  # noqa: E731
    return {'rise': rise * p, 'dy': lerp(dy), 'blur': max(0.0, lerp(blur)),
            'alpha': vb.clamp01(lerp(alpha)), 'scale': lerp(scale)}


def draw_lifted(cv, text, font, cx, cy, p, color, shadow='#000000', dx=0.4, **kw):
    """Draw the line `text` centred at (cx, cy), lifted by progress `p`: the
    letters rise and grow a touch while a soft copy of them in `shadow`
    stays behind and below, dropping, blurring and fading as they climb.
    `dx` is the shadow's sideways drift per pixel of drop (light from the
    upper left); `kw` goes to `lift_shadow`. Returns the text's Box."""
    s = lift_shadow(p, **kw)
    w, h = vb.text.block_size([text], font)
    x, y = cx - w / 2, cy - h / 2

    def glyphs(sub, ox, oy, ink):
        with sub.layer(dx=cx + ox, dy=cy + oy, scale=s['scale']):
            vb.text.draw(sub, [text], font, -w / 2, -h / 2, ink)

    # the shadow stays near the surface: it drops from where the text rests, not from where it is now
    sx, sy = s['dy'] * dx, s['dy']
    type_kit.blurred(cv, vb.Box(x + sx, y + sy, w, h).pad(-w * 0.05), s['blur'],
                     lambda sub: glyphs(sub, sx, sy, shadow), alpha=s['alpha'])
    glyphs(cv, 0, -s['rise'], color)
    k = s['scale']
    return vb.Box(cx - w * k / 2, cy - s['rise'] - h * k / 2, w * k, h * k)


def draw(n, cv):
    p = vb.ease_out_back(demo.phase(n, 0.6, 1.6))
    pw, ph = demo.W * 0.82, demo.H * 0.7
    cv.rect((demo.W - pw) / 2, (demo.H - ph) / 2, pw, ph, PAPER, radius=24)
    box = draw_lifted(cv, 'LIFT OFF', demo.font(round(demo.W * 0.1), 900), demo.W / 2, demo.H / 2, p, demo.ACCENT,
                      shadow='#2b1f18')
    cv.mark('text', *box)


TECHNIQUE = Technique(
    id='drop-shadow-lift',
    name='Drop shadow lift',
    family='typography',
    group='Shadow',
    aliases=('shadow lift', 'lifted text shadow', 'floating text shadow', 'elevation shadow'),
    definition='Text rises toward the viewer while its shadow stays low, sliding further away and '
               'growing softer and fainter, so the words look raised off the page.',
    phrasings=('make the title float up off the background with its shadow dropping away',
               'the words lift and the shadow underneath gets bigger and blurrier',
               'raise the headline so it looks like it is hovering above the page'),
    related=('drop-shadow-breathing', 'drag-lift-with-shadow', 'hover-lift', 'character-rise',
             'long-shadow-extension', 'hover-letter-displacement'),
    api=('videobuilder.techniques.typography.drop_shadow_lift.draw_lifted',
         'videobuilder.techniques.typography.drop_shadow_lift.lift_shadow'),
    demo=lambda: demo.film(draw),
)
