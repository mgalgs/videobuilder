"""Draws dashboard.png once: a screen capture of a made-up analytics app
("Lumen"), the stand-in screenshot the filter looks' demos restyle. Run it
from the repo root to remake the PNG; nothing reads this script at render
time.

    python examples/assets/make_dashboard.py
"""
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
import videobuilder as vb  # noqa: E402
from videobuilder import text  # noqa: E402

for f in sorted(HERE.glob('*.[ot]tf')):
    text.register(f)

W, H = 1280, 960
BG, PANEL, LINE = '#f4f6fa', '#ffffff', '#e2e6ee'
INK, MUTED = '#1b2333', '#6a7385'
BLUE, CORAL, GREEN, AMBER = '#3a6ff0', '#f0644a', '#2fb37a', '#f2b33a'


def F(size, weight=400):
    return vb.Font('Inter', size, weight=weight)


def say(cv, s, f, x, y, colour=INK):
    text.draw(cv, [s], f, x, y, colour)


def main():
    cv = vb.Canvas(W, H, background=BG)
    # the sidebar
    cv.rect(0, 0, 230, H, '#1b2333')
    cv.rect(28, 30, 34, 34, BLUE, radius=9)
    say(cv, 'Lumen', F(24, 700), 74, 33, '#ffffff')
    for i, item in enumerate(('Overview', 'Reports', 'Audience', 'Campaigns', 'Settings')):
        y = 120 + i * 56
        if i == 0:
            cv.rect(16, y - 10, 198, 44, '#2c3a56', radius=10)
        cv.rect(34, y + 2, 18, 18, ('#ffffff' if i == 0 else '#5a6680'), radius=5)
        say(cv, item, F(19, 600 if i == 0 else 500), 66, y, '#ffffff' if i == 0 else '#9aa6bd')
    # the header
    say(cv, 'Overview', F(34, 700), 270, 34)
    say(cv, 'Last 30 days · all channels', F(18, 500), 270, 82, MUTED)
    cv.rect(980, 36, 160, 46, BLUE, radius=12)
    say(cv, 'Export', F(19, 600), 1028, 48, '#ffffff')
    cv.rect(1160, 34, 50, 50, AMBER, radius=25)
    say(cv, 'AK', F(17, 700), 1171, 48, '#ffffff')
    # four stat cards
    stats = (('Visitors', '48,210', '+12.4%', GREEN), ('Sign-ups', '3,982', '+8.1%', GREEN),
             ('Churn', '2.3%', '-0.6%', CORAL), ('Revenue', '$91.4k', '+19.2%', GREEN))
    for i, (name, value, delta, col) in enumerate(stats):
        x = 270 + i * 245
        cv.rect(x, 130, 225, 130, PANEL, radius=16)
        cv.outline(x, 130, 225, 130, LINE, width=2, radius=16)
        say(cv, name, F(18, 500), x + 22, 150, MUTED)
        say(cv, value, F(36, 700), x + 22, 180)
        say(cv, delta, F(17, 600), x + 22, 228, col)
    # the chart
    cv.rect(270, 285, 600, 400, PANEL, radius=16)
    cv.outline(270, 285, 600, 400, LINE, width=2, radius=16)
    say(cv, 'Weekly active users', F(21, 700), 296, 305)
    for k in range(5):
        y = 380 + k * 64
        cv.line(300, y, 845, y, LINE, width=1.5)
    for j in range(12):
        h = 60 + 180 * (0.5 + 0.5 * math.sin(j * 0.7 + 0.4)) * (0.6 + j / 30)
        cv.rect(312 + j * 44, 636 - h, 26, h, BLUE if j != 9 else CORAL, radius=6)
    pts = [(325 + j * 44, 600 - 140 * (0.4 + 0.3 * math.sin(j * 0.55)) - j * 8) for j in range(12)]
    vb.paths.draw(cv, pts, GREEN, width=5)
    for x, y in pts:
        cv.rect(x - 7, y - 7, 14, 14, PANEL, radius=7)
        cv.outline(x - 7, y - 7, 14, 14, GREEN, width=3, radius=7)
    # the donut
    cv.rect(890, 285, 330, 400, PANEL, radius=16)
    cv.outline(890, 285, 330, 400, LINE, width=2, radius=16)
    say(cv, 'Traffic sources', F(21, 700), 916, 305)
    a = -math.pi / 2
    for share, col in ((0.46, BLUE), (0.27, CORAL), (0.17, GREEN), (0.10, AMBER)):
        cv.arc(1055, 465, 95, a, a + share * 2 * math.pi - 0.04, col, width=34)
        a += share * 2 * math.pi
    say(cv, '62%', F(32, 700), 1025, 446)
    for i, (name, col) in enumerate((('Search', BLUE), ('Social', CORAL), ('Email', GREEN), ('Direct', AMBER))):
        x, y = 920 + (i % 2) * 150, 600 + (i // 2) * 36
        cv.rect(x, y + 4, 14, 14, col, radius=4)
        say(cv, name, F(17, 500), x + 24, y, MUTED)
    # the table
    cv.rect(270, 710, 950, 220, PANEL, radius=16)
    cv.outline(270, 710, 950, 220, LINE, width=2, radius=16)
    say(cv, 'Top campaigns', F(21, 700), 296, 730)
    rows = (('Spring launch', 'Email', '12,480', '4.8%'), ('Creator collab', 'Social', '9,113', '3.9%'),
            ('Search brand', 'Search', '7,902', '6.2%'))
    for i, row in enumerate(rows):
        y = 790 + i * 44
        cv.line(296, y - 8, 1194, y - 8, LINE, width=1.5)
        for x, cell in zip((296, 620, 860, 1080), row):
            say(cv, cell, F(18, 600 if x == 296 else 500), x, y, INK if x == 296 else MUTED)
    cv.save_png(str(HERE / 'dashboard.png'))


if __name__ == '__main__':
    main()
