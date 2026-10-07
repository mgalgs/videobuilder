"""Exact PNG frame hashes for the container image's cairo/Pango environment."""
import hashlib
import io
from pathlib import Path

from .film import load

PICKS = {'tour': (45, 142, 247, 330), 'benchmark': (60, 230, 330, 500)}


def manifest(paths):
    lines = []
    for path in paths:
        path = Path(path)
        if path.stem not in PICKS:
            raise ValueError(f'no fixed frame selection for {path.stem}')
        film = load(path)
        for fmt in film.formats:
            for n in PICKS[path.stem]:
                output = io.BytesIO()
                film.frame(n, fmt, scale=.25).surface.write_to_png(output)
                digest = hashlib.sha256(output.getvalue()).hexdigest()
                lines.append(f'{digest}  {path.stem}/{fmt.name}/{n}\n')
    return ''.join(lines)


def check(paths, expected):
    actual = manifest(paths)
    wanted = Path(expected).read_text() if Path(expected).exists() else ''
    if actual != wanted:
        raise ValueError('exact frame hashes changed; inspect the rendered frames, then deliberately '
                         'regenerate deploy/frames.sha256 from the frames image target')
    return actual
