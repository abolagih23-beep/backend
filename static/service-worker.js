const CACHE_NAME = 'shop-pwa-v1';
const ASSETS_TO_CACHE = [
  '/static/index.html',

  // Admin Pages
  '/static/admin/dashboard.html',
  '/static/admin/products.html',
  '/static/admin/sales.html',
  '/static/admin/staff.html',
  '/static/admin/alerts.html',
  '/static/admin/reports.html',
  '/static/admin/settings.html',
  '/static/admin/record_sales.html',

  // Staff Pages
  '/static/staff/sales_entry.html',

  // Icons
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',

  // Other assets
  '/static/image/shop.jpg',
  '/static/css/styles.css',
  '/static/js/main.js'
];

// -----------------------------
// INSTALL: Cache all assets
// -----------------------------
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(ASSETS_TO_CACHE))
      .then(() => self.skipWaiting())
  );
  console.log('[Service Worker] Installed and assets cached');
});

// -----------------------------
// ACTIVATE: Remove old caches
// -----------------------------
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k !== CACHE_NAME)
            .map(k => caches.delete(k))
      )
    )
  );
  return self.clients.claim();
});

// -----------------------------
// FETCH: Cache-first strategy with network fallback
// -----------------------------
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;

  event.respondWith(
    caches.match(event.request).then(cachedResponse => {
      if (cachedResponse) return cachedResponse;

      return fetch(event.request, { cache: 'no-store' })
        .then(networkResponse => {
          // Cache same-origin requests dynamically
          if (event.request.url.startsWith(self.location.origin)) {
            caches.open(CACHE_NAME).then(cache => {
              try {
                cache.put(event.request, networkResponse.clone());
              } catch (e) {
                console.warn('[Service Worker] Cache put failed:', e);
              }
            });
          }
          return networkResponse;
        })
        .catch(() => {
          // Offline fallback for HTML pages
          if (event.request.headers.get('accept')?.includes('text/html')) {
            return caches.match('/static/index.html');
          }
        });
    })
  );
});

// -----------------------------
// MESSAGE HANDLER: Trigger print if needed
// -----------------------------
self.addEventListener('message', event => {
  if (event.data?.type === 'PRINT') {
    self.clients.matchAll().then(clients =>
      clients.forEach(client => client.postMessage({ type: 'PRINT' }))
    );
  }
});

// -----------------------------
// OPTIONAL: Keep console clean
// -----------------------------
self.addEventListener('error', e => console.error('[Service Worker] Error:', e));
self.addEventListener('unhandledrejection', e => console.error('[Service Worker] Unhandled Rejection:', e));