// Version erhöhen, wenn du index.html änderst – dann lädt die App die neue Fassung.
const CACHE = 'karteikasten-1.4.2'; // = APP_VERSION in index.html
const ASSETS = ['./', './index.html', './manifest.webmanifest', './icon-192.png', './icon-512.png', './apple-touch-icon.png', './img/cargo-holds.svg', './img/bow.svg', './img/stern.svg', './img/bulkhead.svg', './img/hatch-covers.svg', './img/double-bottom.svg', './img/engine-room.svg', './img/bridge.svg', './img/funnel.svg'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== location.origin) return;
  if (new URL(req.url).pathname.endsWith('.mp4')) return; // Video direkt vom Netz (Safari braucht Range-Requests)
  if (req.mode === 'navigate') {
    // Online: neueste Version holen; offline: aus dem Cache
    e.respondWith(fetch(req, { cache: 'no-store' }).then(res => {
      const copy = res.clone(); caches.open(CACHE).then(c => c.put('./index.html', copy)); return res;
    }).catch(() => caches.match('./index.html')));
    return;
  }
  e.respondWith(caches.match(req).then(hit => hit || fetch(req)));
});
