"""Self-drawing line chart with a callout: built from videobuilder's own API, so this record only names
it and demos it with its worked example film, `examples/capabilities/line-chart-callout.py` (an
`Example` demo: see schema.py)."""
from ..schema import Capability, Example, Source

CAPABILITY = Capability(
    id='line-chart-callout',
    name='Self-drawing line chart with a callout',
    family='broadcast',
    group='Charts',
    category='Type and data',
    order=7,
    aliases=('trend line reveal', 'animated line graph'),
    definition='Axes first, the line draws itself on, then one point is called out.',
    description=('Honest axes appear first, then every series draws itself on along its own path -- the '
                 'background series in grey, only the hero series in colour -- and once it lands, one '
                 'callout (a dot, a leader line and a short label) points at the single point that '
                 'matters.'),
    phrasings=('Draw the axes first, then let the line draw itself on',
               'Keep the other lines grey, only highlight the hero line',
               'Call out the final point with a dot and a short label'),
    api=('videobuilder.paths.reveal(points, fraction)',
         'videobuilder.paths.draw(cv, points, colour, width=...)',
         'videobuilder.capabilities.broadcast.line_chart_draw_on.draw_line_chart(cv, box, values, progress)',
         'videobuilder.capabilities.broadcast.line_chart_draw_on.reveal_x(points, progress)',
         'videobuilder.capabilities.broadcast.line_chart_draw_on.chart_points(box, values)'),
    doc='skill/make-a-video/reference/api.md',
    demo=Example('examples/capabilities/line-chart-callout.py'),
    source=Source('https://x.com/voxyz_ai/status/2109690569563746755',
                  '@Voxyz_ai',
                  upstream='https://github.com/alchaincyf/huashu-art-motion',
                  upstream_credit='@alchaincyf (huashu-art-motion, MIT)'),
)
