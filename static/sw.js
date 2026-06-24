// ─── Service Worker — Álbum 2026 ─────────────────────────────
const CACHE_NAME = 'album2026-v1';
const STATIC_ASSETS = [
    '/',
    '/static/manifest.json',
    '/static/icon-192.png',
    '/static/icon-512.png',
];

// On install: cache static assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(STATIC_ASSETS);
        })
    );
    self.skipWaiting();
});

// On activate: clean up old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
            )
        )
    );
    self.clients.claim();
});

// On fetch: network-first for API calls, cache-first for static
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // API calls: always try network, fallback gracefully
    if (url.pathname.startsWith('/adjust') || url.pathname.startsWith('/export')) {
        event.respondWith(
            fetch(event.request).catch(() =>
                new Response(JSON.stringify({ error: 'Sin conexión. Los cambios no se guardaron.' }), {
                    status: 503,
                    headers: { 'Content-Type': 'application/json' },
                })
            )
        );
        return;
    }

    // Main page: network-first, fallback to cache
    if (url.pathname === '/') {
        event.respondWith(
            fetch(event.request)
                .then((response) => {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
                    return response;
                })
                .catch(() => caches.match('/'))
        );
        return;
    }

    // Static assets: cache-first
    event.respondWith(
        caches.match(event.request).then((cached) => {
            if (cached) return cached;
            return fetch(event.request).then((response) => {
                if (response && response.status === 200 && response.type !== 'opaque') {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
                }
                return response;
            });
        })
    );
});