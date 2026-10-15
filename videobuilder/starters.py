"""The starter-prompt catalogue shown on the library and New video pages: a
curated jump-start for a brand-new creator, pairing a ready-to-edit prompt
with the capability poster (see capabilities.py) that best shows what it
produces. `needs` names the New-video field the starter most wants filled
in ('files', 'links' or 'none'), used only to highlight that field once the
prompt is applied."""


def _starter(id, title, prompt, poster, needs):
    return {'id': id, 'title': title, 'prompt': prompt, 'poster': poster, 'needs': needs}


STARTERS = (
    _starter(
        'paper-explainer', 'Paper explainer from your files',
        'Use the assets from the attached zip in paper style and create an interesting narrative '
        'and exposition of the topic.',
        'paper-collage', 'files'),
    _starter(
        'launch-from-link', 'Launch video from a link',
        'Make a 30-second launch video for the product at the link. Open on the problem it solves, '
        'show its real screens, and end on a clear call to action.',
        'redrawn-product-ui', 'links'),
    _starter(
        'data-story', 'Data story',
        'Turn the numbers in the attached notes or PDF into a short data story: one clear headline '
        'per chart, numbers that count up, and a takeaway at the end.',
        'bar-charts', 'files'),
    _starter(
        'how-it-works', 'How it works, step by step',
        'Explain how [your topic] works in under a minute, one step at a time, with diagrams that '
        'draw themselves.',
        'drawn-on-diagram', 'none'),
    _starter(
        'photo-story', 'Photo story in order',
        "Tell a short story with the attached photos, in the order I've set. Add gentle camera moves "
        'and a one-line caption on each.',
        'image-treatments', 'files'),
    _starter(
        'vertical-teaser', 'Vertical teaser cut to music',
        'Make a 15-second vertical teaser: bold words that hit on the beat, three short lines that '
        'build to the name, then the logo.',
        'kinetic-typography', 'none'),
)

BY_ID = {s['id']: s for s in STARTERS}
