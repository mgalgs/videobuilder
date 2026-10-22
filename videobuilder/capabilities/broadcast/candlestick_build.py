"""Candlestick build: a price chart that fills in left to right, one candle at
a time. Each candle's body grows from its open to its close, then its wick
stretches out to the session's high and low, coloured by whether the price
rose or fell."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

UP, DOWN = demo.TEAL, demo.ACCENT


def candlestick(cv, x, y_of, ohlc, p, width=36, up=UP, down=DOWN, alpha=1.0):
    """One candle centred on `x`, built to progress `p` in [0, 1]. `ohlc` is
    (open, high, low, close); `y_of(price)` maps a price to a y. The body grows
    from the open to the close over the first 60%, the wick then reaches out
    to the high and low. Returns the candle's colour."""
    o, hi, lo, c = ohlc
    p = vb.clamp01(p)
    if p <= 0:
        return None
    color = up if c >= o else down
    body = vb.ease_out_back(vb.clamp01(p / 0.6))
    wick = vb.ease_out_expo(vb.clamp01((p - 0.4) / 0.6))
    top, bot = max(o, o + (c - o) * body), min(o, o + (c - o) * body)
    y_hi = y_of(top + (hi - max(o, c)) * wick)
    y_lo = y_of(bot - (min(o, c) - lo) * wick)
    if wick > 0:
        cv.line(x, y_hi, x, y_lo, color, width=max(2, width * 0.1), alpha=alpha)
    y0, y1 = y_of(top), y_of(bot)
    cv.rect(x - width / 2, y0, width, max(2, y1 - y0), color, radius=min(4, width * 0.12), alpha=alpha)
    cv.mark('candle', x - width / 2, min(y_hi, y0), width, max(y_lo, y1) - min(y_hi, y0))
    return color


def candlestick_build(cv, box, series, t, lo=None, hi=None, stagger=0.25, each=0.5, width=None,
                      up=UP, down=DOWN):
    """A candlestick chart in `box` (x, y, w, h) built `t` seconds in: candle
    `i` of `series` (a list of (open, high, low, close)) starts at
    `i * stagger` and takes `each` seconds. The price range defaults to the
    series' own low and high."""
    x, y, w, h = box
    lo = min(s[2] for s in series) if lo is None else lo
    hi = max(s[1] for s in series) if hi is None else hi
    step = w / len(series)
    width = width or step * 0.5

    def y_of(price):
        return y + h - (price - lo) / (hi - lo) * h

    for i, ohlc in enumerate(series):
        candlestick(cv, x + step * (i + 0.5), y_of, ohlc, (t - i * stagger) / each, width, up, down)
    return y_of


SERIES = [(42, 50, 36, 47), (47, 58, 44, 56), (56, 60, 49, 51), (51, 66, 50, 64), (64, 74, 60, 71),
          (71, 73, 58, 61), (61, 68, 55, 66), (66, 82, 64, 79), (79, 84, 70, 73), (73, 90, 72, 87)]


def draw(n, cv):
    left, top, right, bottom = 130, 80, demo.W - 70, demo.H - 70
    lo, hi = 30, 95
    label = demo.mono(16, 600)
    for v in range(30, 100, 15):
        gy = bottom - (v - lo) / (hi - lo) * (bottom - top)
        cv.line(left, gy, right, gy, demo.LINE, width=1)
        vb.text.draw(cv, [str(v)], label, left - 50, gy - 9, demo.MUTED)
    cv.line(left, bottom, right, bottom, demo.MUTED, width=2)
    t = n / demo.FPS - 0.3
    candlestick_build(cv, (left, top, right - left, bottom - top), SERIES, t, lo=lo, hi=hi,
                      stagger=0.2, each=0.55)
    shown = min(len(SERIES) - 1, max(0, int(t / 0.2)))
    o, h_, l_, c = SERIES[shown]
    if t > 0:
        txt = f'O {o}  H {h_}  L {l_}  C {c}'
        vb.text.draw(cv, [txt], demo.mono(20, 700), left, 34, UP if c >= o else DOWN)


CAPABILITY = Capability(
    id='candlestick-build',
    name='Candlestick build',
    family='broadcast',
    group='Charts',
    aliases=('OHLC bars', 'price candle reveal', 'candlestick chart animation'),
    definition='A stock-style price chart fills in left to right, each candle growing its body from '
               'open to close and then stretching its thin wick out to the high and low.',
    phrasings=('animate a stock chart where the candles pop in one by one',
               'build up the trading candles across the chart',
               'show the price bars appearing day by day with their wicks'),
    related=('embers', 'light-trail-logo-reveal', 'milestone-marker-pop', 'refresh-bar',
             'audio-waveform-bars', 'kuramoto-synchronization'),
    api=('videobuilder.capabilities.broadcast.candlestick_build.candlestick_build',
         'videobuilder.capabilities.broadcast.candlestick_build.candlestick'),
    demo=lambda: demo.film(draw),
)
