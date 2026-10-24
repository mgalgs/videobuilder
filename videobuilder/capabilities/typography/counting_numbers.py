"""Numbers that count up: built from videobuilder's own API, so this record only names it and demos it
with its worked example film, `examples/capabilities/counting-numbers.py` (an `Example` demo: see
schema.py)."""
from ..schema import Capability, Example

CAPABILITY = Capability(
    id='counting-numbers',
    name='Numbers that count up',
    family='typography',
    group='Counting',
    category='Type and data',
    order=4,
    aliases=('number ticker', 'rolling number', 'stat counter', 'currency counter', 'comma-grouped count'),
    definition='A hero stat counts from zero to its final value.',
    description=('A big number counts up to its final value on a spring, the way a benchmark or a result '
                 'should land: with weight, not just appearing.'),
    phrasings=('Count this number up to 2.4x',
               'Make the stat count up as it lands, not just appear',
               'Count up to the final value over the first second'),
    api=('vb.spring_at / vb.interpolate drives the displayed value',
         "f'{value * min(1, p):.1f}'",
         'videobuilder.capabilities.typography.number_count_up.count_up(value, p)',
         'videobuilder.capabilities.typography.number_count_up.draw_count_up(cv, value, font, x, y, p, color)',
         'videobuilder.capabilities.typography.decimal_counter_with_formatting.format_count(value, decimals)',
         'videobuilder.capabilities.typography.decimal_counter_with_formatting.count_value(start, end, p)'),
    doc='skill/make-a-video/reference/api.md',
    demo=Example('examples/capabilities/counting-numbers.py'),
)
