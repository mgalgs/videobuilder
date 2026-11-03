// The app shell only (see pwa.py, which fills in VERSION). Everything that isn't a
// version-stamped script or style, or an icon, is left to the network: API answers,
// render and job state, media and pages are never cached, because a stale answer is
// worse than an error.
const VERSION = __VERSION__;
const PREFIX = 'vb-shell-';
const CACHE = PREFIX + VERSION;

const OFFLINE = '<!doctype html><html lang="en"><head><meta charset="utf-8">' +
  '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">' +
  '<meta name="theme-color" content="#0d0d10"><title>Offline · videobuilder</title>' +
  '<style>:root{color-scheme:dark}body{margin:0;min-height:100vh;display:flex;align-items:center;' +
  'justify-content:center;background:#0d0d10;color:#f4f4f2;font:16px/1.5 system-ui,sans-serif;' +
  'text-align:center;padding:24px env(safe-area-inset-right) 24px env(safe-area-inset-left);' +
  'box-sizing:border-box}h1{font-size:1.3rem;margin:0 0 .4rem}p{color:#a9a9b2;margin:0 0 1.2rem}' +
  'button{min-height:44px;padding:.5rem 1.2rem;border:0;border-radius:10px;background:#e5483b;' +
  'color:#fff;font:inherit;font-weight:600}</style></head><body><main><h1>You’re offline</h1>' +
  '<p>videobuilder needs a connection. Check yours, then try again.</p>' +
  '<button onclick="location.reload()">Try again</button></main></body></html>';

function isShell(url) {
  if (url.origin !== self.location.origin || url.pathname.includes('/api/')) return false;
  if (/^\/icons\/[a-z0-9-]+\.png$/.test(url.pathname)) return true;
  // Only the URLs pwa.editor_html stamps with *this* version: an older worker still
  // running during a deploy sends the new page's assets to the network, not its cache.
  return /\/(director|suggest|settings_card)\.(js|css)$/.test(url.pathname) &&
    url.searchParams.get('v') === VERSION;
}

self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', event => event.waitUntil((async () => {
  for (const key of await caches.keys()) {
    if (key.startsWith(PREFIX) && key !== CACHE) await caches.delete(key);
  }
  await self.clients.claim();
})()));

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;
  if (request.mode === 'navigate') {
    event.respondWith(fetch(request).catch(() => new Response(OFFLINE, {
      status: 503, headers: {'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store'},
    })));
    return;
  }
  if (!isShell(new URL(request.url))) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const hit = await cache.match(request);
    if (hit) return hit;
    const response = await fetch(request);
    if (response.ok) await cache.put(request, response.clone());
    return response;
  })());
});
