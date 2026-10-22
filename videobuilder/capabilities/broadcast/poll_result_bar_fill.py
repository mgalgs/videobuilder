"""Poll result bar fill: a social-style poll reveals its results -- each
option's row fills from the left to its share of the vote while the
percentage counts up beside it, then the winning option lights up."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def poll_shares(votes):
    """Whole-number percentages for a list of vote counts that add up to
    exactly 100 (largest remainder), as a poll shows them. All zeros: all 0."""
    total = sum(votes)
    if total <= 0:
        return [0] * len(votes)
    raw = [100 * v / total for v in votes]
    out = [int(r) for r in raw]
    by_rest = sorted(range(len(votes)), key=lambda i: raw[i] - out[i], reverse=True)
    for i in by_rest[:100 - sum(out)]:
        out[i] += 1
    return out


def draw_poll_results(cv, x, y, w, labels, votes, p, row_h=44, gap=12, stagger=0.12,
                      fill='#4a4e58', win=demo.ACCENT, track=demo.LINE, ink=demo.INK, size=22,
                      ease=vb.ease_out_quint):
    """Draw a poll's result rows from top-left (x, y), `w` wide, at reveal
    progress `p` (0 -> 1). Each row is a rounded track holding the option's
    label; its bar fills from the left to the option's share of `votes` while
    the percentage on the right counts up. Rows start `stagger` of the reveal
    apart, so the fills ripple down the list; the leading option's bar fades
    from `fill` to `win` over the last fifth and its label turns bold.
    Returns the Box of each row's filled part, top to bottom."""
    shares = poll_shares(votes)
    lead = max(range(len(votes)), key=lambda i: votes[i]) if votes else -1
    span = max(1e-6, 1 - stagger * (len(votes) - 1))
    settle = vb.clamp01((p - 0.8) / 0.2)
    boxes = []
    for i, (label, share) in enumerate(zip(labels, shares)):
        q = ease(vb.clamp01((p - i * stagger) / span))
        ry = y + i * (row_h + gap)
        r = row_h / 2
        cv.rect(x, ry, w, row_h, track, radius=r)
        fw = w * share / 100 * q
        winner = i == lead
        color = demo.kit.mix(fill, win, settle) if winner else fill
        if fw > 0:
            cv.rect(x, ry, fw, row_h, color, radius=min(r, fw / 2))
        weight = 800 if winner and settle > 0.5 else 600
        f = demo.font(size, weight)
        th = vb.text.line_height(f)
        vb.text.draw(cv, [label], f, x + r, ry + (row_h - th) / 2, ink)
        pct = f'{round(share * q)}%'
        pf = demo.font(size, weight)
        vb.text.draw(cv, [pct], pf, x + w - r - vb.text.measure(pct, pf), ry + (row_h - th) / 2, ink)
        boxes.append(vb.Box(x, ry, fw, row_h))
    return boxes


# The demo: a poll card; its results fill in, then the winner is called.
LABELS = ('Morning', 'Lunch break', 'Evening', 'Late night')
VOTES = (412, 168, 905, 241)
CARD_W, PAD = 600, 32


def draw(n, cv):
    row_h, gap = 44, 12
    card_h = PAD * 2 + 58 + len(LABELS) * (row_h + gap) - gap + 38
    x, y = (demo.W - CARD_W) / 2, (demo.H - card_h) / 2
    cv.shadow(x, y, CARD_W, card_h, radius=18, dy=10, blur=28, color=(0, 0, 0, 0.45))
    cv.rect(x, y, CARD_W, card_h, '#1c1f26', radius=18)
    vb.text.draw(cv, ['When do you scroll most?'], demo.font(28, 800), x + PAD, y + PAD, demo.INK)
    p = demo.phase(n, 0.4, 2.4)
    rows_y = y + PAD + 58
    boxes = draw_poll_results(cv, x + PAD, rows_y, CARD_W - 2 * PAD, LABELS, VOTES, p, row_h=row_h, gap=gap)
    total = round(sum(VOTES) * vb.ease_out_quint(demo.phase(n, 0.4, 1.6)))
    vb.text.draw(cv, [f'{total:,} votes · Final results'], demo.font(17, 500),
                 x + PAD, rows_y + len(LABELS) * (row_h + gap) - gap + 14, demo.MUTED)
    for i, b in enumerate(boxes):
        if b.w > 0:
            cv.mark(f'bar{i}', *b)


CAPABILITY = Capability(
    id='poll-result-bar-fill',
    name='Poll result bar fill',
    family='broadcast',
    group='Social media',
    aliases=('poll results reveal', 'vote bar fill', 'social poll animation', 'survey result bars'),
    definition='Each answer in a poll gets a bar that fills to its share of the votes while its percentage '
               'counts up, and the most popular answer is highlighted when they settle.',
    phrasings=('show the poll results filling in like on social media',
               'animate the vote percentages growing for each option',
               'reveal which answer won the poll with bars filling up'),
    related=('percentage-fill-bar', 'bar-chart-race', 'bar-grow', 'star-rating-fill', 'scroll-progress-bar',
             'area-fill-sweep'),
    api=('videobuilder.capabilities.broadcast.poll_result_bar_fill.draw_poll_results',
         'videobuilder.capabilities.broadcast.poll_result_bar_fill.poll_shares'),
    demo=lambda: demo.film(draw),
)
