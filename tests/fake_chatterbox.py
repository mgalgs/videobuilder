"""Stands in for Chatterbox's interpreter running chatterbox_worker.py: the
same protocol, with a tone per phrase (0.05 s per character, pitched by
the seed and the voice clip's size) instead of a model. Every argv and
text it gets is appended, as JSON, to $FAKE_CHATTERBOX_LOG."""
import argparse
import base64
import json
import math
import os
import sys

RATE = 24000
log = open(os.environ['FAKE_CHATTERBOX_LOG'], 'a', encoding='utf-8')
log.write(json.dumps({'argv': sys.argv[1:]}) + '\n')
log.flush()
p = argparse.ArgumentParser()
p.add_argument('worker')
for flag in ('--repo', '--revision', '--cache-dir', '--voice', '--seed', '--exaggeration', '--cfg-weight'):
    p.add_argument(flag)
a = p.parse_args()
if os.environ.get('FAKE_CHATTERBOX_FAIL'):
    print(json.dumps({'error': os.environ['FAKE_CHATTERBOX_FAIL'], 'install': True}), flush=True)
    sys.exit(1)
hz = 200 + 10 * int(a.seed) + (os.path.getsize(a.voice) % 50 if a.voice else 0)
print(json.dumps({'ready': True, 'rate': RATE}), flush=True)
for line in sys.stdin:
    text = json.loads(line)['text']
    log.write(json.dumps({'text': text}) + '\n')
    log.flush()
    n = int(0.05 * len(text) * RATE)
    body = [int(0.5 * 32767 * math.sin(2 * math.pi * hz * i / RATE)) for i in range(n)]
    pcm = b''.join(v.to_bytes(2, 'little', signed=True) for v in [0] * 4800 + body + [0] * 7200)
    print(json.dumps({'samples': base64.b64encode(pcm).decode('ascii')}), flush=True)
