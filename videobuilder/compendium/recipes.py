"""Reference recipes: short declarative films built only from the seed
components, to prove the format is enough to compose a whole video from.
Each names its components in order, with their slots filled and their length
in beats, plus a tempo and formats; `catalog.build_recipe_film` turns one into
an ordinary `videobuilder.Film`.
"""
from .kit import ACCENT, TEAL, sample_photo
from .schema import Recipe, RecipeStep

PRODUCT_TEASER = Recipe(
    id='product-teaser',
    title='Product teaser',
    description='A 15-20s teaser: a beat-pop title, a hero stat, a bar chart, then an end card.',
    bpm=60,
    formats=('16x9', '9x16'),
    steps=(
        RecipeStep('beat-pop-title', 5, {
            'headline': 'Ship it today', 'subtitle': 'One push, every environment.', 'accent': ACCENT}),
        RecipeStep('stat-counter', 4, {
            'value': 3.1, 'label': 'faster deploys this quarter', 'suffix': 'x'}),
        RecipeStep('bar-chart', 4, {
            'title': 'Deploys a day', 'series': [('Before', 2.0), ('Staging', 5.0), ('Now', 9.0)], 'accent': TEAL}),
        RecipeStep('end-card', 4, {
            'headline': 'Ship it today', 'line2': 'Try it on your next release.', 'accent': ACCENT}),
    ),
)

EXPLAINER = Recipe(
    id='how-it-works',
    title='How it works',
    description='A 20-30s explainer: a kinetic title, a picture, a slide transition, a chart, a stat, an end card.',
    bpm=60,
    formats=('16x9', '9x16'),
    steps=(
        RecipeStep('kinetic-title', 4, {'headline': 'Here is how it works', 'accent': ACCENT}),
        RecipeStep('image-showcase', 4, {'image': sample_photo(), 'caption': 'Your product, dropped in'}),
        RecipeStep('overlap-slide', 3, {
            'from_label': 'Draft', 'to_label': 'Live', 'from_color': ACCENT, 'to_color': TEAL}),
        RecipeStep('bar-chart', 5, {
            'title': 'Time to ship', 'series': [('Manual', 6.0), ('Scripted', 3.0), ('Automated', 1.0)]}),
        RecipeStep('stat-counter', 4, {'value': 92, 'label': 'fewer manual steps', 'suffix': '%'}),
        RecipeStep('end-card', 4, {
            'headline': 'That is the whole flow', 'line2': 'No new dependencies, no new steps.', 'accent': TEAL}),
    ),
)

RECIPES = (PRODUCT_TEASER, EXPLAINER)
