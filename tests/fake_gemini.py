"""A local HTTP server standing in for Gemini's generateContent endpoint,
for `say --engine gemini` tests: the real urllib call in speech.Gemini hits
this, not Google. `requests` records each call's JSON body; by default
answers with a randomly pitched tone (Gemini can't be seeded, so a real
re-request would sound different too), sized by the phrase's text length,
so a test that expects a cached phrase's bytes to stay put would fail if
the code asked again. `queue` lets a test script exactly what the next
call(s) get, to exercise retries and error paths. A request carrying
audio (`listen`) gets markdown notes naming the audio's type and size back
instead, after `delay` seconds.
"""
import base64
import json
import math
import random
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RATE = 24000


def _tone(text):
    n = int(0.05 * len(text) * RATE)
    hz = 200 + random.random() * 400   # no seed: a real re-request would sound different too
    body = [int(0.5 * 32767 * math.sin(2 * math.pi * hz * i / RATE)) for i in range(n)]
    return b''.join(v.to_bytes(2, 'little', signed=True) for v in [0] * 480 + body + [0] * 480)


class FakeGemini:
    def __init__(self):
        self.requests = []
        self.responses = []   # [(status, json body), ...], consumed in request order
        self.delay = 0
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                n = int(self.headers.get('Content-Length') or 0)
                body = json.loads(self.rfile.read(n) or b'{}')
                outer.requests.append(body)
                if outer.delay:
                    # Not time.sleep: the say tests patch that out globally.
                    threading.Event().wait(outer.delay)
                if outer.responses:
                    status, payload = outer.responses.pop(0)
                else:
                    status, payload = 200, outer._default(body)
                data = json.dumps(payload).encode('utf-8')
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *a):
                pass

        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.url = f'http://127.0.0.1:{self.httpd.server_address[1]}/v1beta/models/{{model}}:generateContent'
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def queue(self, status, payload):
        self.responses.append((status, payload))

    @staticmethod
    def _default(body):
        audio = [p['inlineData'] for p in body['contents'][0]['parts'] if 'inlineData' in p]
        if audio:
            size = len(base64.b64decode(audio[0]['data']))
            return {'candidates': [{'content': {'parts': [
                {'text': f"## Overall\nA song ({audio[0]['mimeType']}, {size} bytes).\n"}]}}]}
        text = body['contents'][0]['parts'][0].get('text', '')
        data = base64.b64encode(_tone(text)).decode('ascii')
        return {'candidates': [{'content': {'parts': [
            {'inlineData': {'mimeType': f'audio/L16;rate={RATE}', 'data': data}}]}}]}
