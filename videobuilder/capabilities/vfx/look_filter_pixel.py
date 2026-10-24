"""8-bit pixel filter: one look of the Looks capability, built from videobuilder's own API, so this
record only names it and demos it with its worked example film, `examples/capabilities/look-filter-
pixel.py` (an `Example` demo: see schema.py)."""
from ..schema import Capability, Example, Source

CAPABILITY = Capability(
    id='look-filter-pixel',
    name='8-bit pixel filter',
    family='vfx',
    group='Filter looks',
    aliases=('mosaic', 'pixelize', 'low-res downsample', 'pixel dissolve', 'depixelate', 'mosaic reveal'),
    definition='Any picture as chunky 8-bit pixels, stepped like an old game.',
    description=('Restyles whatever the video draws: shrunk to a chunky grid in a 16-colour game palette '
                 'and scaled back up hard-edged on faint scan lines, while a rolling bar steps down the '
                 "screen at 8 fps. Draw the picture underneath at the filter's stepped time and it steps "
                 'with it. To pixelate one layer of a drawn scene instead -- a sprite, a HUD label that '
                 'should stay blocky -- draw it into a pixelated layer: it is drawn at a fraction of the '
                 'resolution and scaled back up with nearest-neighbour filtering, any text in it '
                 'pixelating too, its motion held two frames at a time.'),
    phrasings=('Make my product demo look like an old 8-bit video game',
               'Render this as retro 8-bit pixel art',
               'Make the motion choppier, like an old game, not smooth 30fps'),
    api=("with looks.filter(cv, 'pixel', t): draw_as_usual(n, cv)",
         "looks.get_filter('pixel').step(t)  # draw the picture at this time to step with the filter",
         'cv.pixelated(factor)  # one blocky layer of a drawn scene; draw with the canvas it yields',
         'stepped_n = (n // 2) * 2  # 15fps motion on a 30fps film',
         'videobuilder.capabilities.vfx.pixelation.pixelate(cv, scene, block)  # an amount the filter can animate'),
    doc='skill/make-a-video/reference/looks.md',
    demo=Example('examples/capabilities/look-filter-pixel.py'),
    old_ids=('pixel-art-layer',),
    source=Source('https://x.com/voxyz_ai/status/2109690569563746755',
                  '@Voxyz_ai',
                  upstream='https://github.com/alchaincyf/huashu-art-motion',
                  upstream_credit='@alchaincyf (huashu-art-motion, MIT)'),
)
