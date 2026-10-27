"""Stands in for Chatterbox's interpreter running chatterbox_worker.py: the
same protocol, with no real model. Every argv it gets, and every request's
own log-worthy bit (a synth's text, a convert's or transcribe's input
length), is appended as JSON to $FAKE_CHATTERBOX_LOG.

synth: a tone per phrase (0.05 s per character, pitched by the seed and
the voice clip's size) instead of a model. convert: pcm negated and offset
by the --convert-to clip's size, so a test can tell it ran, and with which
target, without a real voice model. transcribe: the next string from
$FAKE_CHATTERBOX_TRANSCRIPTS (a JSON list), repeating the last one once
the list runs out; '' with none set.
"""
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
p.add_argument('--ops', default='synth')
for flag in ('--repo', '--revision', '--cache-dir', '--voice', '--convert-to', '--seed', '--exaggeration',
             '--cfg-weight'):
    p.add_argument(flag)
a = p.parse_args()
if os.environ.get('FAKE_CHATTERBOX_FAIL'):
    print(json.dumps({'error': os.environ['FAKE_CHATTERBOX_FAIL'], 'install': True}), flush=True)
    sys.exit(1)
hz = 200 + 10 * int(a.seed or 0) + (os.path.getsize(a.voice) % 50 if a.voice else 0)
transcripts = json.loads(os.environ.get('FAKE_CHATTERBOX_TRANSCRIPTS') or '[]')
print(json.dumps({'ready': True, 'rate': RATE}), flush=True)
for line in sys.stdin:
    req = json.loads(line)
    if 'text' in req:
        text = req['text']
        log.write(json.dumps({'text': text}) + '\n')
        log.flush()
        n = int(0.05 * len(text) * RATE)
        body = [int(0.5 * 32767 * math.sin(2 * math.pi * hz * i / RATE)) for i in range(n)]
        pcm = b''.join(v.to_bytes(2, 'little', signed=True) for v in [0] * 4800 + body + [0] * 7200)
        print(json.dumps({'samples': base64.b64encode(pcm).decode('ascii')}), flush=True)
    elif 'convert' in req:
        pcm_in = base64.b64decode(req['convert'])
        log.write(json.dumps({'convert': len(pcm_in)}) + '\n')
        log.flush()
        tag = os.path.getsize(a.convert_to) % 50 if a.convert_to else 0
        out = bytearray()
        for i in range(0, len(pcm_in) - 1, 2):
            v = int.from_bytes(pcm_in[i:i + 2], 'little', signed=True)
            out += max(-32768, min(32767, -v + tag)).to_bytes(2, 'little', signed=True)
        print(json.dumps({'samples': base64.b64encode(bytes(out)).decode('ascii')}), flush=True)
    elif 'transcribe' in req:
        pcm_in = base64.b64decode(req['transcribe'])
        log.write(json.dumps({'transcribe': len(pcm_in)}) + '\n')
        log.flush()
        word = transcripts.pop(0) if len(transcripts) > 1 else (transcripts[0] if transcripts else '')
        print(json.dumps({'transcript': word}), flush=True)
