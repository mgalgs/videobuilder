"""Versioned, persistent film worker protocol on stdin/stdout."""
import json
import os
import sys
import traceback
from contextlib import redirect_stdout

from . import __version__, edits
from .preview import Session

PROTOCOL = 1


def serve():
    output = sys.stdout.buffer
    output.write(json.dumps({'protocol': PROTOCOL, 'version': __version__}).encode() + b'\n')
    output.flush()
    session = None
    for line in sys.stdin.buffer:
        try:
            request = json.loads(line)
            path = os.path.abspath(request['path'])
            with redirect_stdout(sys.stderr):
                if session is None or session.path != path:
                    session = Session(path, poll=0)
                op = request['op']
                if op == 'check':
                    session.check()
                    value = {'version': session.version, 'error': session.error}
                elif op == 'info':
                    session.check()
                    value = session.info()
                elif op == 'frame':
                    session.check()
                    value = session.png(int(request.get('frame', 0)), request.get('format'),
                                        float(request.get('scale', 1)), bool(request.get('overlay', False)))
                elif op == 'edit':
                    segment = request['segment']
                    field = request['field']
                    key = request.get('key')
                    value = request['value']
                    tl = edits.timeline(path)
                    try:
                        found = tl.find(segment)
                    except KeyError:
                        raise ValueError(f'no segment named {segment!r} in the timeline') from None
                    if field == 'data' and key not in found.data:
                        raise ValueError(f'segment {segment}: data has no key {key!r} to override')
                    before = found.until if field == 'until' else found.data[key]
                    if field == 'until' and (isinstance(value, bool) or not isinstance(value, (int, float))):
                        raise ValueError(f'until must be a number of beats, not {value!r}')
                    if field == 'data' and not isinstance(value, str):
                        raise ValueError('copy must be a string')
                    value = {'before': before, 'toml': edits.change_text(path, segment, field, key, value)}
                else:
                    raise ValueError(f'unknown operation {op!r}')
            if isinstance(value, bytes):
                header = {'ok': True, 'length': len(value)}
                output.write(json.dumps(header).encode() + b'\n' + value)
            else:
                output.write(json.dumps({'ok': True, 'value': value}).encode() + b'\n')
        except Exception as exc:
            output.write(json.dumps({'ok': False, 'error': str(exc) if isinstance(exc, ValueError)
                                     else traceback.format_exc()}).encode() + b'\n')
        output.flush()
