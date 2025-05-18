// Cache name
const CACHE_NAME = 'agromap-cache-v1';

// Resources to cache
const RESOURCES_TO_CACHE = [
    '/',
    '/static/css/map.css',
    '/static/css/responsive.css',
    'https://unpkg.com/leaflet@1.7.1/dist/leaflet.css',
    'https://unpkg.com/leaflet@1.7.1/dist/leaflet.js',
    'https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js',
    'https://cdn.jsdelivr.net/npm/chart.js',
    '/static/data/uzbekistan_regions.geojson'
];

// Install service worker
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                return cache.addAll(RESOURCES_TO_CACHE);
            })
    );
});

// Fetch event handler
self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request)
            .then((response) => {
                // Return cached version or fetch from network
                return response || fetch(event.request)
                    .then((response) => {
                        // Cache new responses for future offline use
                        if (response.status === 200) {
                            const responseClone = response.clone();
                            caches.open(CACHE_NAME)
                                .then((cache) => {
                                    cache.put(event.request, responseClone);
                                });
                        }
                        return response;
                    });
            })
            .catch(() => {
                // Return offline fallback if both cache and network fail
                return caches.match('/offline.html');
            })
    );
});
