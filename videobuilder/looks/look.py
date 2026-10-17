"""The Look type: a name, a title, a line on what moves, and its paint function."""
import re


def _key(name):
    return re.sub(r'[^a-z0-9]+', '-', str(name).lower()).strip('-')


class Look:
    """A named look: `paint(cv, scene, t, age, **opts)` draws the whole
    scene (every pixel of its w x h) in this style.

    - `t`: film time in seconds -- the look's motion runs on it, so it
      carries on through a cut or a wipe.
    - `age`: seconds since this look came on screen, for one-off moves (a
      wave rising, a drawing drawing itself in); defaults to `t`.
    - `opts`: look-specific extras, each optional (see the look's own module).

    `title` is the human name, `line` says what moves; `aliases` are other
    names `get` accepts."""

    def __init__(self, name, title, line, paint, aliases=()):
        if _key(name) != name:
            raise ValueError(f'look name {name!r} must be lowercase words joined by hyphens')
        self.name, self.title, self.line, self._paint = name, title, line, paint
        self.aliases = tuple(aliases)

    def __call__(self, cv, scene, t, age=None, **opts):
        self._paint(cv, scene, t, t if age is None else age, **opts)

    paint = __call__

    def __repr__(self):
        return f'<look {self.name}: {self.title}>'
