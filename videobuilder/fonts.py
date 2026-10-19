"""The font list the suggest layer's model prompt and the Fonts picker share
(see suggest.py, director.js/suggest.js): every font family a builder
actually has, with where it comes from and a one-line character. Three are
registered from `examples/assets` for the demos and the benchmark; the rest
ship in the release image's Debian packages (`fonts-dejavu-core`,
`fonts-liberation`; see deploy/Dockerfile) and are resolved by fontconfig at
whatever path this machine installed them to, so this list stays accurate
across distros without hard-coding one.

Add a font here when the release image or examples/assets gains one;
nothing else should hand-roll this list."""
import functools
import os
import subprocess

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _asset(name):
    return os.path.join(REPO_ROOT, 'examples', 'assets', name)


# id, family (the real name text.register/vb.Font take), where it comes from
# (for the prompt and the picker's byline), a one-line character, and either
# an asset path (bundled, always present) or None (resolved on this machine
# by fontconfig: see `_system_path`).
FONTS = (
    {'id': 'inter', 'family': 'Inter', 'source': 'examples/assets (Inter-Variable.ttf)',
     'about': 'The clean default sans; variable weight.', 'asset': _asset('Inter-Variable.ttf')},
    {'id': 'cantarell', 'family': 'Cantarell', 'source': 'examples/assets (Cantarell-VF.otf)',
     'about': 'Rounded, friendly sans; variable weight.', 'asset': _asset('Cantarell-VF.otf')},
    {'id': 'source-code-pro', 'family': 'Source Code Pro', 'source': 'examples/assets (SourceCodeVF-Upright.otf)',
     'about': 'Monospace; typewriter, terminal, code.', 'asset': _asset('SourceCodeVF-Upright.otf')},
    {'id': 'dejavu-sans', 'family': 'DejaVu Sans', 'source': 'the release image (fonts-dejavu-core)',
     'about': 'Wide, open humanist sans.', 'asset': None},
    {'id': 'dejavu-sans-mono', 'family': 'DejaVu Sans Mono', 'source': 'the release image (fonts-dejavu-core)',
     'about': 'Monospace with open shapes.', 'asset': None},
    {'id': 'dejavu-serif', 'family': 'DejaVu Serif', 'source': 'the release image (fonts-dejavu-core)',
     'about': 'A sturdy book serif.', 'asset': None},
    {'id': 'liberation-sans', 'family': 'Liberation Sans', 'source': 'the release image (fonts-liberation)',
     'about': 'Neutral grotesque, Arial-like metrics.', 'asset': None},
    {'id': 'liberation-serif', 'family': 'Liberation Serif', 'source': 'the release image (fonts-liberation)',
     'about': 'A newspaper serif, Times-like metrics.', 'asset': None},
    {'id': 'liberation-mono', 'family': 'Liberation Mono', 'source': 'the release image (fonts-liberation)',
     'about': 'Monospace, Courier-like typewriter.', 'asset': None},
)

_BY_ID = {f['id']: f for f in FONTS}


@functools.lru_cache(maxsize=None)
def _system_path(family):
    """The file fontconfig resolves `family` to on this machine, or None (no
    `fc-match`, or it isn't installed here). Cached: this never changes while
    the process runs."""
    try:
        out = subprocess.run(['fc-match', '-f', '%{file}', family], capture_output=True, timeout=2, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    path = out.stdout.decode('utf-8', 'replace').strip()
    return path if out.returncode == 0 and path and os.path.isfile(path) else None


def ids():
    return set(_BY_ID)


def get(id):
    """The font entry called `id` ({id, family, source, about}); KeyError if none."""
    font = _BY_ID.get(id)
    if font is None:
        raise KeyError(id)
    return {k: v for k, v in font.items() if k != 'asset'}


def path(id):
    """Where `id`'s font file actually is on this machine right now, or None
    (a system font fontconfig can't resolve here -- the picker's card shows
    its sample in a fallback face rather than failing)."""
    font = _BY_ID.get(id)
    if font is None:
        raise KeyError(id)
    return font['asset'] or _system_path(font['family'])


def public():
    """Every font, for the Fonts picker and the model's catalog block."""
    return [get(f['id']) for f in FONTS]
