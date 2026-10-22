"""Game clock countdown: a scoreboard clock runs a period down to zero, holds
there with an end-of-period flag, then resets for the next period with the
period badge changing."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

PERIOD_COLORS = (demo.ACCENT, demo.TEAL, '#e8b931', '#8f8cf2')


def game_clock(t, length=720.0, periods=4, start=None, rate=1.0, intermission=1.0):
    """The clock `t` seconds in, as `(period, remaining, ended)`. Period 1
    starts at `start` seconds left (default `length`), later ones at `length`;
    the clock runs at `rate` game seconds per second. At zero it holds for
    `intermission` seconds with `ended` true, then the next period starts.
    After the last period it stays at zero, ended. Before 0 it holds at rest."""
    t = max(t, 0.0)
    left = length if start is None else start
    for period in range(1, periods + 1):
        run = left / rate
        if t < run:
            return period, left - t * rate, False
        t -= run
        if t < intermission or period == periods:
            return period, 0.0, True
        t -= intermission
        left = length
    return periods, 0.0, True


def format_clock(remaining, tenths_below=60.0):
    """`remaining` seconds as a game clock reads it: `M:SS` (seconds rounded
    up, so it shows 0:00 only at the buzzer), or `S.t` under `tenths_below`
    seconds (pass 0 to always show minutes)."""
    if remaining < tenths_below:
        return f'{math.ceil(remaining * 10 - 1e-9) / 10:.1f}'
    whole = math.ceil(remaining - 1e-9)
    return f'{whole // 60}:{whole % 60:02d}'


def _tabular(cv, text, font, cx, cy, color):
    """`text` centred at (cx, cy) with every digit in a cell as wide as the
    widest digit, so the clock never shuffles sideways as it ticks."""
    cell = max(vb.text.measure(d, font) for d in '0123456789')
    advs = [cell if ch.isdigit() else vb.text.measure(ch, font) for ch in text]
    _, h = vb.text.block_size([text], font)
    x = cx - sum(advs) / 2
    for ch, adv in zip(text, advs):
        vb.text.draw(cv, [ch], font, x + (adv - vb.text.measure(ch, font)) / 2, cy - h / 2, color)
        x += adv
    return vb.Box(cx - sum(advs) / 2, cy - h / 2, sum(advs), h)


def draw_game_clock(cv, t, cx, cy, length=720.0, periods=4, start=None, rate=1.0, intermission=1.0,
                    tenths_below=60.0, colors=PERIOD_COLORS, ink=demo.INK, muted=demo.MUTED,
                    panel='#1d1f26', scale=1.0, label='GAME CLOCK', ended_label='END OF PERIOD'):
    """Draw a scoreboard game clock centred at (cx, cy) as it reads `t`
    seconds in (see `game_clock`): a panel with a period badge in the
    period's colour (from `colors`, cycling), the time in big tabular digits,
    and a bar of the period left. At zero the digits and caption turn the
    period colour and the panel flashes once for the buzzer. Returns the
    panel's Box."""
    period, remaining, ended = game_clock(t, length, periods, start, rate, intermission)
    color = colors[(period - 1) % len(colors)]
    w, h = 520 * scale, 290 * scale
    x, y = cx - w / 2, cy - h / 2
    cv.shadow(x, y, w, h, radius=22 * scale, dy=12 * scale, blur=30 * scale, color=(0, 0, 0, 0.5))
    cv.rect(x, y, w, h, panel, radius=22 * scale)
    cv.outline(x, y, w, h, demo.LINE, width=2 * scale, radius=22 * scale)
    if ended:
        since = t - _zero_time(period, length, start, rate, intermission)
        flash = max(0.0, 1 - since / 0.35)
        if flash:
            cv.rect(x, y, w, h, color, radius=22 * scale, alpha=0.35 * flash)
            cv.outline(x, y, w, h, color, width=4 * scale, radius=22 * scale, alpha=flash)
    badge_f = demo.font(22 * scale, 800)
    badge = f'PERIOD {period}'
    bw, bh = vb.text.block_size([badge], badge_f)
    pad = 14 * scale
    cv.rect(x + 28 * scale, y + 26 * scale, bw + 2 * pad, bh + pad, color, radius=8 * scale)
    vb.text.draw(cv, [badge], badge_f, x + 28 * scale + pad, y + 26 * scale + pad / 2, demo.BG)
    side_f = demo.font(20 * scale, 700)
    side = f'OF {periods}'
    sw, sh = vb.text.block_size([side], side_f)
    vb.text.draw(cv, [side], side_f, x + w - 28 * scale - sw, y + 26 * scale + (bh + pad - sh) / 2, muted)
    _tabular(cv, format_clock(remaining, tenths_below), demo.font(118 * scale, 800), cx, cy + 6 * scale,
             color if ended else ink)
    bar_y, bar_x, bar_w = y + h - 66 * scale, x + 32 * scale, w - 64 * scale
    cv.rect(bar_x, bar_y, bar_w, 6 * scale, demo.LINE, radius=3 * scale)
    full = length if period > 1 or start is None else start
    if remaining > 0:
        cv.rect(bar_x, bar_y, bar_w * remaining / full, 6 * scale, color, radius=3 * scale)
    cap_f = demo.font(18 * scale, 700)
    cap = ended_label if ended else label
    cw, _ = vb.text.block_size([cap], cap_f)
    vb.text.draw(cv, [cap], cap_f, cx - cw / 2, bar_y + 20 * scale, color if ended else muted)
    return vb.Box(x, y, w, h)


def _zero_time(period, length, start, rate, intermission):
    """When (in seconds) period `period` reached zero, in step with `game_clock`."""
    first = (length if start is None else start) / rate
    return first + (period - 1) * (intermission + length / rate)


def draw(n, cv):
    t = n / demo.FPS - 0.2
    # period 1 has 2 s left; it buzzes at 2.2 s and period 2 resets to 12:00
    box = draw_game_clock(cv, t, demo.W / 2, demo.H / 2, start=2.0, intermission=0.45)
    cv.mark('clock', *box)


CAPABILITY = Capability(
    id='game-clock-countdown',
    name='Game clock countdown',
    family='broadcast',
    group='Sports graphics',
    aliases=('game clock', 'period clock', 'scoreboard clock', 'shot clock'),
    definition='A scoreboard clock ticks a period down to zero, flags the end of the period, '
               'then resets to full time as the period badge steps to the next one.',
    phrasings=('a sports scoreboard clock running down to the buzzer',
               'show the match timer hit zero and roll over to the next quarter',
               'a basketball-style clock counting down with the period number'),
    related=('number-count-down', 'stopwatch-count-up', 'timecode-counter', 'timing', 'number-count-up',
             'decimal-counter-with-formatting'),
    api=('videobuilder.capabilities.broadcast.game_clock_countdown.draw_game_clock',
         'videobuilder.capabilities.broadcast.game_clock_countdown.game_clock',
         'videobuilder.capabilities.broadcast.game_clock_countdown.format_clock'),
    demo=lambda: demo.film(draw),
)
