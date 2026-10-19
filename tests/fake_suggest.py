"""A fake OpenAI-compatible chat-completions endpoint on a local port, for the
suggest client and endpoint tests: nothing here touches the real network.

`requests` records every (method, path, headers, body) served. `answer` is
the JSON (a dict or list) the next call's `choices[0].message.content`
holds; `stall` seconds delays the response (for timeout/cancellation tests).
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeSuggest:
    def __init__(self, answer=None, usage=None):
        self.requests = []
        self.answer = answer if answer is not None else {'items': []}
        self.usage = usage if usage is not None else {'prompt_tokens': 100, 'completion_tokens': 20,
                                                       'total_tokens': 120}
        self.stall = 0
        self.status = 200
        self.raw_body = None  # overrides the usual {"choices": [...]} shape when set
        self.lock = threading.Lock()
        self.closed_early = threading.Event()
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                n = int(self.headers.get('Content-Length') or 0)
                body = self.rfile.read(n)
                with outer.lock:
                    outer.requests.append({'method': 'POST', 'path': self.path,
                                           'headers': dict(self.headers.items()), 'body': json.loads(body or b'{}')})
                    stall, status = outer.stall, outer.status
                if stall:
                    time.sleep(stall)
                try:
                    if outer.raw_body is not None:
                        payload = outer.raw_body
                    else:
                        payload = json.dumps({
                            'choices': [{'message': {'content': json.dumps(outer.answer)}}],
                            'usage': outer.usage,
                        }).encode()
                    self.send_response(status)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                except (BrokenPipeError, ConnectionResetError, OSError):
                    outer.closed_early.set()

            def log_message(self, *a):
                pass

        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.base = f'http://127.0.0.1:{self.httpd.server_address[1]}/v1'
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()
