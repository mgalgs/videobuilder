"""Atomic file writes: write to a temp file beside the target, then rename."""
import json
import os


def write_atomic(path, data, encoding='utf-8'):
    """Write `data` (str or bytes) to `path` by writing a sibling `.tmp` file
    and renaming it over `path`, so a reader never sees a partial write."""
    path = os.fspath(path)
    tmp = path + '.tmp'
    if isinstance(data, bytes):
        with open(tmp, 'wb') as fh:
            fh.write(data)
    else:
        with open(tmp, 'w', encoding=encoding, newline='\n') as fh:
            fh.write(data)
    os.replace(tmp, path)


def write_json_atomic(path, obj, newline=False, **dump_kwargs):
    """`write_atomic` with `obj` as JSON. `dump_kwargs` (e.g. indent, ensure_ascii)
    go straight to `json.dumps`; `newline` adds a trailing newline some callers want
    and others don't, so each caller's exact on-disk format is unchanged."""
    text = json.dumps(obj, **dump_kwargs)
    write_atomic(path, text + '\n' if newline else text, encoding='utf-8')
