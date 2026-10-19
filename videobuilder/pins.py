"""Reading and rewriting a video's videobuilder pin, shared by the version
upgrade path (versions.py), the sandboxed worker's environment choice
(workers.py) and the draft scope guard (drafts.py, which lets a builder's own
pin raise through on the same terms `Versions.upgrade` would apply) so all
three agree on what the pin line looks like and what counts as "only the
version changed".
"""
import re

_PIN = re.compile(r'^\s*videobuilder\s*==\s*([0-9]+(?:\.[0-9]+){1,3})\s*(?:#.*)?$', re.I)
_PIN_REF = re.compile(r'@v?([0-9]+(?:\.[0-9]+){1,3})(?:\b|$)')


def numbers(version):
    return tuple(map(int, version.split('.')))


def version_in(text):
    """The videobuilder version this requirements.txt text pins, or 'unknown'."""
    for line in text.splitlines():
        match = _PIN.match(line.rstrip('\r\n'))
        if not match and 'videobuilder' in line.lower():
            match = _PIN_REF.search(line)
        if match:
            return match.group(1)
    return 'unknown'


def repin(text, version):
    """`text` with only the version of its videobuilder pin changed, found the
    way `version_in` finds it."""
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        match = _PIN.match(line.rstrip('\r\n'))
        if not match and 'videobuilder' in line.lower():
            match = _PIN_REF.search(line)
        if match:
            lines[i] = line[:match.start(1)] + version + line[match.end(1):]
            return ''.join(lines)
    raise ValueError('no videobuilder pin to upgrade')


def raised_only(base_text, tip_text, ceiling):
    """(old, new) when `tip_text` is exactly `base_text` with its videobuilder
    pin raised to a version above `old` and at most `ceiling`, and nothing
    else in the file changed -- the same edit `Versions.upgrade` itself would
    make. None otherwise, including when either text has no recognizable pin."""
    old, new = version_in(base_text), version_in(tip_text)
    if old == 'unknown' or new == 'unknown':
        return None
    if not (numbers(old) < numbers(new) <= numbers(ceiling)):
        return None
    try:
        if repin(base_text, new) != tip_text:
            return None
    except ValueError:
        return None
    return old, new
