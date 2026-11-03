"""Home-screen install: the manifest, icons and service worker served
signed-out, the head tags on every top-level page, the worker's fetch
routing (run in node), and the icons themselves."""
import json
import math
import re
import shutil
import subprocess
import unittest
from importlib import resources

from PIL import Image

from tests import fixtures
from videobuilder import __version__, pwa
from videobuilder.editor import _page

ICON_DIR = resources.files('videobuilder').joinpath('icons')

HEAD_TAGS = (
    '<link rel="manifest" href="/manifest.webmanifest">',
    '<meta name="theme-color" content="#0d0d10">',
    '<link rel="apple-touch-icon" href="/icons/apple-touch-icon.png">',
    '<meta name="apple-mobile-web-app-capable" content="yes">',
    '<meta name="mobile-web-app-capable" content="yes">',
    '<meta name="apple-mobile-web-app-title" content="videobuilder">',
    '<meta name="apple-mobile-web-app-status-bar-style" content="black">',
    'navigator.serviceWorker.register("/sw.js")',
)


class Offline:
    def setUp(self):
        super().setUp()
        self.library.whats_new.remote_videos = False  # /whats-new would fetch the release videos


class Routes(Offline, fixtures.AccountMixin, fixtures.LibraryFixture, unittest.TestCase):
    """Accounts on, and no cookie and no identity header: what a browser fetching
    the manifest, or a guest on the sign-in page, sends."""

    def test_install_files_are_served_signed_out_with_their_types(self):
        expected = {'/manifest.webmanifest': 'application/manifest+json',
                    '/sw.js': 'text/javascript; charset=utf-8',
                    '/icons/icon-192.png': 'image/png', '/icons/icon-512.png': 'image/png',
                    '/icons/icon-maskable-512.png': 'image/png', '/icons/apple-touch-icon.png': 'image/png'}
        for path, ctype in expected.items():
            with self.subTest(path=path):
                code, _, headers = self.request_full(path)
                self.assertEqual(code, 200)
                self.assertEqual(headers['Content-Type'], ctype)
                self.assertEqual(headers['Cache-Control'], 'no-cache')

    def test_the_manifest_is_relative_and_standalone(self):
        _, manifest, _ = self.request_full('/manifest.webmanifest')
        manifest = json.loads(manifest)
        self.assertEqual((manifest['name'], manifest['short_name']), ('videobuilder', 'videobuilder'))
        self.assertEqual((manifest['start_url'], manifest['scope'], manifest['display']), ('./', './', 'standalone'))
        self.assertEqual((manifest['theme_color'], manifest['background_color']), ('#0d0d10', '#0d0d10'))
        self.assertNotIn('://', json.dumps(manifest))
        self.assertEqual({(i['src'], i['sizes'], i['purpose']) for i in manifest['icons']},
                         {('/icons/icon-192.png', '192x192', 'any'), ('/icons/icon-512.png', '512x512', 'any'),
                          ('/icons/icon-maskable-512.png', '512x512', 'maskable')})
        for icon in manifest['icons']:
            self.assertEqual(self.request_full(icon['src'])[0], 200)

    def test_the_worker_carries_the_version(self):
        _, body, _ = self.request_full('/sw.js')
        self.assertIn(f'const VERSION = "{__version__}";'.encode(), body)
        self.assertNotIn(b'__VERSION__', body)

    def test_other_paths_beside_them_still_need_a_session(self):
        self.assertEqual(self.request('/icons/other.png')[0], 200)  # the sign-in page, not a file
        self.assertIn(b'Sign in', self.request('/icons/other.png')[1])
        self.assertEqual(self.request('/api/project')[0], 401)


class Heads(Offline, fixtures.AccountMixin, fixtures.LibraryFixture, unittest.TestCase):
    def assertHead(self, page, where):
        head = re.search(r'<head>(.*?)</head>', page, re.S)
        self.assertIsNotNone(head, where)
        for tag in HEAD_TAGS:
            self.assertIn(tag, head.group(1), where)

    def test_every_top_level_page_carries_the_install_tags(self):
        for path in ('/login', '/signup'):
            code, page = self.request(path)
            self.assertEqual(code, 200, path)
            self.assertHead(page.decode(), path)
        cookie = self.admin_login()
        self.seed('acme/launch', film=True)
        for path in ('/', '/new', '/account', '/whats-new', '/capabilities', '/capabilities/typography',
                     '/compendium', '/v/acme/launch/'):
            code, page = self.request(path, headers={'Cookie': cookie})
            self.assertEqual(code, 200, path)
            self.assertHead(page.decode(), path)

    def test_the_editor_stamps_its_own_assets_and_keeps_viewport_fit_cover(self):
        cookie = self.admin_login()
        self.seed('acme/launch', film=True)
        _, page = self.request('/v/acme/launch/', headers={'Cookie': cookie})
        for page in (page.decode(), _page().decode()):
            self.assertHead(page, 'editor')
            self.assertIn('viewport-fit=cover', page)
            for asset in ('director.css', 'suggest.css', 'settings_card.css'):
                self.assertIn(f'href="{asset}?v={__version__}"', page)
            for asset in ('director.js', 'suggest.js', 'settings_card.js'):
                self.assertIn(f'src="{asset}?v={__version__}"', page)
        code, js, headers = self.request_full(f'/v/acme/launch/director.js?v={__version__}',
                                              headers={'Cookie': cookie})
        self.assertEqual((code, headers['Content-Type']), (200, 'text/javascript; charset=utf-8'))
        self.assertTrue(js)


# Runs sw.js in a vm context with a fake CacheStorage and network; prints one JSON report.
WORKER_HARNESS = r"""
const vm = require('vm');
const SRC = %s, VERSION = %s, ORIGIN = 'https://review.example';
const handlers = {}, stores = new Map(), fetched = [];
let online = true;
const caches = {
  keys: async () => [...stores.keys()],
  delete: async key => stores.delete(key),
  open: async key => {
    if (!stores.has(key)) stores.set(key, new Map());
    const m = stores.get(key);
    return {match: async r => m.has(r.url) ? m.get(r.url).clone() : undefined,
            put: async (r, res) => { m.set(r.url, res); }};
  },
};
const fetch = async req => {
  fetched.push(req.url);
  if (!online) throw new TypeError('Failed to fetch');
  return new Response('network', {status: 200});
};
const self = {location: new URL(ORIGIN + '/sw.js'), addEventListener: (type, f) => { handlers[type] = f; },
              skipWaiting: () => {}, clients: {claim: async () => {}}};
vm.runInContext(SRC, vm.createContext({self, caches, fetch, Response, URL, console}));

async function dispatch(path, mode = 'no-cors', method = 'GET') {
  let answer = null;
  handlers.fetch({request: {url: ORIGIN + path, mode, method}, respondWith: p => { answer = p; }});
  if (!answer) return 'passed to the network';
  const r = await answer;
  return r.status + ' ' + (await r.text());
}
async function seed(path, body) {
  const cache = await caches.open('vb-shell-' + VERSION);
  await cache.put({url: ORIGIN + path}, new Response(body));
}

(async () => {
  const out = {};
  await caches.open('vb-shell-0.0.1');
  await caches.open('vb-shell-' + VERSION);
  await caches.open('someone-elses-cache');
  let wait;
  handlers.activate({waitUntil: p => { wait = p; }});
  await wait;
  out.caches_after_activate = [...stores.keys()].sort();

  const asset = '/v/acme/launch/director.js?v=' + VERSION;
  out.asset_first = [await dispatch(asset), fetched.length];
  out.asset_second = [await dispatch(asset), fetched.length];
  out.icon = await dispatch('/icons/icon-192.png');
  out.icon_again = [await dispatch('/icons/icon-192.png'), fetched.length];

  // Each of these sits in the cache, poisoned: none may ever be answered from it.
  const never = ['/api/name', '/v/acme/launch/api/project', '/v/acme/launch/api/notes/n1.png',
                 '/v/acme/launch/api/attachments/0123abcd', '/v/acme/launch/api/sources/clip.mp4',
                 '/v/acme/launch/api/thumbnail', '/capabilities/showcase-16x9.mp4',
                 '/v/acme/launch/director.js', '/v/acme/launch/director.js?v=0.0.1',
                 '/v/acme/launch/', '/'];
  for (const path of never) await seed(path, 'stale');
  out.never = {};
  for (const path of never) out.never[path] = await dispatch(path);
  out.navigate_online = await dispatch('/v/acme/launch/', 'navigate');
  out.post = await dispatch(asset, 'no-cors', 'POST');
  out.cross_origin = await (async () => {
    let answer = null;
    handlers.fetch({request: {url: 'https://elsewhere.example/icons/icon-192.png', mode: 'no-cors', method: 'GET'},
                    respondWith: p => { answer = p; }});
    return answer ? 'answered' : 'passed to the network';
  })();

  online = false;
  out.navigate_offline = await dispatch('/v/acme/launch/', 'navigate');
  out.asset_offline = await dispatch(asset);
  console.log(JSON.stringify(out));
})().catch(e => { console.error(e); process.exit(1); });
"""


@unittest.skipUnless(shutil.which('node'), 'node is not available in this environment')
class WorkerRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        script = WORKER_HARNESS % (json.dumps(pwa.worker().decode()), json.dumps(__version__))
        result = subprocess.run(['node', '-'], input=script.encode(), capture_output=True, timeout=60)
        if result.returncode:
            raise AssertionError(result.stderr.decode())
        cls.out = json.loads(result.stdout)

    def test_activating_a_new_version_deletes_only_older_versions_caches(self):
        self.assertEqual(self.out['caches_after_activate'], sorted([f'vb-shell-{__version__}', 'someone-elses-cache']))

    def test_a_versioned_static_asset_is_answered_from_the_cache(self):
        self.assertEqual(self.out['asset_first'], ['200 network', 1])
        self.assertEqual(self.out['asset_second'], ['200 network', 1])  # no second fetch
        self.assertEqual(self.out['icon_again'], ['200 network', 2])
        self.assertEqual(self.out['asset_offline'], '200 network')

    def test_api_media_unversioned_assets_and_pages_never_come_from_the_cache(self):
        for path, answer in self.out['never'].items():
            with self.subTest(path=path):
                self.assertEqual(answer, 'passed to the network')
        self.assertEqual(self.out['navigate_online'], '200 network')
        self.assertEqual(self.out['post'], 'passed to the network')
        self.assertEqual(self.out['cross_origin'], 'passed to the network')

    def test_an_offline_navigation_gets_the_offline_page_not_a_cached_one(self):
        status, _, body = self.out['navigate_offline'].partition(' ')
        self.assertEqual(status, '503')
        self.assertIn('You’re offline', body)
        self.assertNotIn('stale', body)


class Icons(unittest.TestCase):
    RED = (0xe5, 0x48, 0x3b)

    def open(self, name):
        with ICON_DIR.joinpath(name).open('rb') as f:
            image = Image.open(f)
            image.load()
        return image

    def test_the_four_sizes(self):
        for name, size in (('icon-192.png', 192), ('icon-512.png', 512), ('icon-maskable-512.png', 512),
                           ('apple-touch-icon.png', 180)):
            self.assertEqual(self.open(name).size, (size, size), name)

    def test_full_bleed_icons_are_opaque(self):
        # iOS paints transparency black, and a maskable icon is cropped to any shape.
        for name in ('icon-maskable-512.png', 'apple-touch-icon.png'):
            alpha = self.open(name).convert('RGBA').getchannel('A')
            self.assertEqual(alpha.getextrema(), (255, 255), name)

    def test_the_maskable_mark_stays_inside_the_central_80_percent_circle(self):
        image = self.open('icon-maskable-512.png').convert('RGB')
        size = image.size[0]
        centre, radius = size / 2, size * 0.4
        pixels = image.load()
        marked = 0
        for y in range(size):
            for x in range(size):
                if max(abs(a - b) for a, b in zip(pixels[x, y], self.RED)) > 8:
                    marked += 1
                    self.assertLessEqual(math.hypot(x + .5 - centre, y + .5 - centre), radius, (x, y))
        self.assertGreater(marked, 1000)  # the white triangle is really there


if __name__ == '__main__':
    unittest.main()
