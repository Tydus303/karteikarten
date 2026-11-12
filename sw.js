// Version erhöhen, wenn du index.html änderst – dann lädt die App die neue Fassung.
const CACHE = 'karteikasten-1.4.4'; // = APP_VERSION in index.html
const ASSETS = ['./', './index.html', './manifest.webmanifest', './icon-192.png', './icon-512.png', './apple-touch-icon.png',
  './img/block-coefficient.svg', './img/bow.svg', './img/bridge.svg', './img/bulkhead.svg', './img/cargo-holds.svg', './img/double-bottom.svg', './img/engine-room.svg', './img/funnel.svg', './img/hatch-covers.svg', './img/lashing.svg', './img/part-accommodation.svg', './img/part-ahead.svg', './img/part-air-draft.svg', './img/part-amidships.svg', './img/part-anchor.svg', './img/part-astern.svg', './img/part-auxiliaries.svg', './img/part-ballast-tanks.svg', './img/part-bow-thruster.svg', './img/part-bridge-wings.svg', './img/part-bulbous-bow.svg', './img/part-catwalk.svg', './img/part-draught.svg', './img/part-frames.svg', './img/part-freeboard.svg', './img/part-hull-machinery.svg', './img/part-hull.svg', './img/part-lashing-bridges.svg', './img/part-lifeboat.svg', './img/part-loa.svg', './img/part-main-deck.svg', './img/part-main-engine.svg', './img/part-manifold.svg', './img/part-propeller.svg', './img/part-ramp.svg', './img/part-rudder.svg', './img/part-shaft-generator.svg', './img/part-superstructure.svg', './img/part-tank-top.svg', './img/part-vent.svg', './img/quay.svg', './img/sec-beam.svg', './img/sec-cell-guides.svg', './img/sec-double-hull.svg', './img/sec-hatch-coaming.svg', './img/sec-self-trimming.svg', './img/sec-tween-deck.svg', './img/sec-understow.svg', './img/stern.svg', './img/type-bulker.svg', './img/type-capesize.svg', './img/type-cargo-gear.svg', './img/type-chemical.svg', './img/type-coaster.svg', './img/type-conro.svg', './img/type-container.svg', './img/type-crude.svg', './img/type-feeder.svg', './img/type-gearless.svg', './img/type-heavylift.svg', './img/type-livestock.svg', './img/type-lng.svg', './img/type-mpp.svg', './img/type-ore.svg', './img/type-pctc.svg', './img/type-product.svg', './img/type-reefer.svg', './img/type-ropax.svg', './img/type-roro.svg', './img/type-semisub.svg', './img/type-tug.svg'];

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
