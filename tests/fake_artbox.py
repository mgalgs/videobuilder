"""A fake artbox image service on a local port, for the Pictures tests (and,
run as `python3 -m tests.fake_artbox PORT`, for trying the panel by hand:
there each job is queued for a few seconds, runs a few more, then is done).

`jobs` maps a job id to its JSON; a test moves a job along with `finish`,
`fail` or by editing it. `requests` records every (method, path) served.
"""
import io
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

from PIL import Image, ImageDraw

COLOURS = [(220, 60, 50), (60, 140, 220), (240, 190, 40), (90, 180, 110)]


def png(colour, size=64, matte=False):
    """A small PNG: a coloured disc, on grey or (for a matte) on transparency."""
    im = Image.new('RGBA', (size, size), (0, 0, 0, 0) if matte else (128, 128, 128, 255))
    ImageDraw.Draw(im).ellipse((size // 8, size // 8, size * 7 // 8, size * 7 // 8), fill=colour + (255,))
    out = io.BytesIO()
    (im if matte else im.convert('RGB')).save(out, 'PNG')
    return out.getvalue()


class FakeArtbox:
    def __init__(self, auto=None, size=64):
        self.jobs = {}
        self.files = {}
        self.requests = []
        self.submitted = []
        self.gpu = {'free': True}
        self.auto = auto
        self.size = size
        self.overrides = {}
        self.redirect = None
        self.lock = threading.Lock()
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                outer.requests.append(('GET', self.path))
                outer._get(self)

            def do_POST(self):
                outer.requests.append(('POST', self.path))
                n = int(self.headers.get('Content-Length') or 0)
                outer._post(self, json.loads(self.rfile.read(n) or b'{}'))

            def log_message(self, *a):
                pass

        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.base = f'http://127.0.0.1:{self.httpd.server_address[1]}'
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def _send(self, handler, code, body, ctype='application/json', headers=None):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        handler.send_response(code)
        handler.send_header('Content-Type', ctype)
        handler.send_header('Content-Length', str(len(data)))
        for k, v in (headers or {}).items():
            handler.send_header(k, v)
        handler.end_headers()
        handler.wfile.write(data)

    def _post(self, handler, body):
        if handler.path != '/api/images':
            return self._send(handler, 404, {'error': 'no'})
        with self.lock:
            job_id = f'20261016-1420{len(self.jobs):02d}'
            self.jobs[job_id] = {'id': job_id, 'kind': 'image', 'tag': body.get('tag'), 'n': body['n'],
                                 'size': body.get('size'), 'matte': body.get('matte'), 'prompt': body['prompt'],
                                 'state': 'queued', 'created': time.time()}
            self.submitted.append(body)
        self._send(handler, 200, self.jobs[job_id])

    def _get(self, handler):
        path = handler.path
        if self.redirect:
            return self._send(handler, 302, {}, headers={'Location': self.redirect})
        if path == '/api/gpu':
            return self._send(handler, 200, self.gpu)
        if path.startswith('/api/jobs/'):
            job_id = path[len('/api/jobs/'):]
            if job_id in self.overrides:
                return self._send(handler, 200, self.overrides[job_id])
            job = self.jobs.get(job_id)
            if job is None:
                return self._send(handler, 404, {'error': 'no such job'})
            if self.auto:
                self._auto(job)
            return self._send(handler, 200, job)
        if path.startswith('/files/'):
            data = self.files.get(unquote(path))
            if data is None:
                return self._send(handler, 404, {'error': 'no such file'})
            return self._send(handler, 200, data, 'image/png')
        self._send(handler, 404, {'error': 'no'})

    def _auto(self, job):
        age = time.time() - job['created']
        queued, running = self.auto
        if job['state'] == 'queued' and age > queued:
            job['state'] = 'running'
        if job['state'] == 'running' and age > queued + running:
            self.finish(job['id'])

    def finish(self, job_id):
        job = self.jobs[job_id]
        images = []
        prompt = job['prompt'].split(',')[0][:40]
        for i in range(job['n']):
            name = f'2026-10-16-14h20m4{i}s_seed{i + 3}_{prompt}.png'
            colour = COLOURS[(len(self.files) + i) % len(COLOURS)]
            self.files[f'/files/{job_id}/{name}'] = png(colour, self.size)
            image = {'name': name, 'seed': i + 3}
            if job['matte']:
                image['matte'] = name[:-4] + '_matte.png'
                self.files[f'/files/{job_id}/{image["matte"]}'] = png(colour, self.size, matte=True)
            images.append(image)
        job.update(state='done', images=images)

    def fail(self, job_id):
        self.jobs[job_id]['state'] = 'failed'


if __name__ == '__main__':
    fake = FakeArtbox(auto=(8, 10), size=512)
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    if port:
        fake.close()
        fake.httpd = ThreadingHTTPServer(('127.0.0.1', port), fake.httpd.RequestHandlerClass)
        fake.base = f'http://127.0.0.1:{port}'
        threading.Thread(target=fake.httpd.serve_forever, daemon=True).start()
    print(fake.base, flush=True)
    while True:
        time.sleep(3600)
