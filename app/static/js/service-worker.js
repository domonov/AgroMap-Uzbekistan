const CACHE_NAME = 'agromap-cache-v2';
const STATIC_CACHE = 'agromap-static-v2';
const DYNAMIC_CACHE = 'agromap-dynamic-v2';
const API_CACHE = 'agromap-api-v2';

// Static resources that rarely change
const STATIC_URLS = [
  '/',
  '/static/css/style.css',
  '/static/js/main.js',
  '/static/js/service-worker.js',
  '/static/images/markers/wheat.png',
  '/static/images/markers/cotton.png',
  '/static/images/markers/potato.png',
  '/static/images/markers/rice.png',
  '/static/images/markers/corn.png',
  '/static/images/markers/barley.png',
  'https://unpkg.com/leaflet@1.7.1/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.7.1/dist/leaflet.js',
  'https://unpkg.com/leaflet-draw@1.0.4/dist/leaflet.draw.css',
  'https://unpkg.com/leaflet-draw@1.0.4/dist/leaflet.draw.js',
  'https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css',
  'https://cdn.jsdelivr.net/npm/flatpickr',
  'https://unpkg.com/leaflet.markercluster@1.4.1/dist/leaflet.markercluster.js'
];

// API endpoints that can be cached temporarily
const CACHEABLE_APIS = [
  '/api/weather',
  '/api/crop-reports',
  '/api/market-prices'
];

// Cache configurations
const CACHE_CONFIG = {
  static: {
    maxAge: 7 * 24 * 60 * 60 * 1000, // 7 days
    maxEntries: 50
  },
  dynamic: {
    maxAge: 24 * 60 * 60 * 1000, // 24 hours
    maxEntries: 100
  },
  api: {
    maxAge: 30 * 60 * 1000, // 30 minutes
    maxEntries: 50
  }
};

// Cache resources during installation with improved strategy
self.addEventListener('install', event => {
  console.log('Service Worker installing...');
  event.waitUntil(
    Promise.all([
      // Cache static resources
      caches.open(STATIC_CACHE).then(cache => {
        console.log('Caching static resources');
        return cache.addAll(STATIC_URLS);
      }),
      // Initialize other caches
      caches.open(DYNAMIC_CACHE),
      caches.open(API_CACHE)
    ]).then(() => {
      console.log('Service Worker installation complete');
      return self.skipWaiting();
    })
  );
});

// Clean up old caches during activation with improved cleanup
self.addEventListener('activate', event => {
  console.log('Service Worker activating...');
  const currentCaches = [STATIC_CACHE, DYNAMIC_CACHE, API_CACHE];
  
  event.waitUntil(
    Promise.all([
      // Clean up old caches
      caches.keys().then(cacheNames => {
        return Promise.all(
          cacheNames.map(cacheName => {
            if (!currentCaches.includes(cacheName)) {
              console.log('Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      }),
      // Clean up expired entries
      cleanExpiredCaches()
    ]).then(() => {
      console.log('Service Worker activation complete');
      return self.clients.claim();
    })
  );
});

// Enhanced fetch handling with multiple caching strategies
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Handle different types of requests with appropriate strategies
  if (request.method === 'GET') {
    if (isStaticResource(request)) {
      // Cache First strategy for static resources
      event.respondWith(cacheFirst(request, STATIC_CACHE));
    } else if (isAPIRequest(request)) {
      // Network First with fallback for API requests
      event.respondWith(networkFirstWithFallback(request, API_CACHE));
    } else if (isNavigationRequest(request)) {
      // Network First for navigation requests
      event.respondWith(networkFirstForNavigation(request));
    } else {
      // Stale While Revalidate for other resources
      event.respondWith(staleWhileRevalidate(request, DYNAMIC_CACHE));
    }
  } else if (request.method === 'POST' && isAPIRequest(request)) {
    // Handle POST requests for offline functionality
    event.respondWith(handleAPIPost(request));
  }
});

// Cache First Strategy - good for static resources
async function cacheFirst(request, cacheName) {
  try {
    const cache = await caches.open(cacheName);
    const cachedResponse = await cache.match(request);
    
    if (cachedResponse && !isExpired(cachedResponse)) {
      return cachedResponse;
    }
    
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const responseClone = networkResponse.clone();
      await cache.put(request, responseClone);
    }
    return networkResponse;
  } catch (error) {
    console.error('Cache First error:', error);
    const cache = await caches.open(cacheName);
    return cache.match(request) || createOfflineResponse(request);
  }
}

// Network First with Fallback - good for API requests
async function networkFirstWithFallback(request, cacheName) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName);
      const responseClone = networkResponse.clone();
      await cache.put(request, responseClone);
      return networkResponse;
    }
    throw new Error('Network response not ok');
  } catch (error) {
    console.log('Network failed, trying cache for:', request.url);
    const cache = await caches.open(cacheName);
    const cachedResponse = await cache.match(request);
    
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // Return fallback data for specific API endpoints
    return createAPIFallback(request);
  }
}

// Network First for Navigation - good for HTML pages
async function networkFirstForNavigation(request) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      const responseClone = networkResponse.clone();
      await cache.put(request, responseClone);
      return networkResponse;
    }
    throw new Error('Network response not ok');
  } catch (error) {
    const cache = await caches.open(DYNAMIC_CACHE);
    const cachedResponse = await cache.match(request);
    
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // Return offline page
    return caches.match('/') || createOfflineResponse(request);
  }
}

// Stale While Revalidate - good for dynamic content
async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cachedResponse = await cache.match(request);
  
  const fetchPromise = fetch(request).then(networkResponse => {
    if (networkResponse.ok) {
      const responseClone = networkResponse.clone();
      cache.put(request, responseClone);
    }
    return networkResponse;
  }).catch(error => {
    console.error('Network error:', error);
    return cachedResponse;
  });
  
  return cachedResponse || fetchPromise;
}

// Enhanced background sync for stored requests with retry logic
self.addEventListener('sync', event => {
  console.log('Background sync event:', event.tag);
  
  if (event.tag === 'sync-reports') {
    event.waitUntil(syncReports());
  } else if (event.tag === 'sync-weather-data') {
    event.waitUntil(syncWeatherData());
  } else if (event.tag === 'sync-market-data') {
    event.waitUntil(syncMarketData());
  }
});

// Handle POST requests for offline functionality
async function handleAPIPost(request) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      return networkResponse;
    }
    throw new Error('Network response not ok');
  } catch (error) {
    console.log('Storing POST request for later sync:', request.url);
    
    // Store the request for later sync
    const requestData = {
      url: request.url,
      method: request.method,
      headers: Object.fromEntries(request.headers.entries()),
      body: await request.text(),
      timestamp: Date.now()
    };
    
    await storeForSync(requestData);
    
    // Register for background sync
    if ('serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype) {
      const registration = await self.registration;
      await registration.sync.register('sync-reports');
    }
    
    // Return success response
    return new Response(
      JSON.stringify({ success: true, queued: true, message: 'Request queued for sync' }),
      { 
        status: 202,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

// Helper functions for request classification
function isStaticResource(request) {
  const url = new URL(request.url);
  return STATIC_URLS.some(staticUrl => 
    staticUrl.includes(url.pathname) || url.pathname.includes('/static/')
  ) || url.pathname.endsWith('.css') || url.pathname.endsWith('.js') || 
     url.pathname.endsWith('.png') || url.pathname.endsWith('.jpg') || 
     url.pathname.endsWith('.svg');
}

function isAPIRequest(request) {
  const url = new URL(request.url);
  return url.pathname.startsWith('/api/');
}

function isNavigationRequest(request) {
  return request.mode === 'navigate' || 
         (request.method === 'GET' && request.headers.get('accept').includes('text/html'));
}

function isExpired(response) {
  const cacheTime = response.headers.get('sw-cache-time');
  if (!cacheTime) return false;
  
  const url = new URL(response.url);
  let maxAge = CACHE_CONFIG.dynamic.maxAge;
  
  if (isStaticResource({ url: response.url })) {
    maxAge = CACHE_CONFIG.static.maxAge;
  } else if (isAPIRequest({ url: response.url })) {
    maxAge = CACHE_CONFIG.api.maxAge;
  }
  
  return Date.now() - parseInt(cacheTime) > maxAge;
}

// Create fallback responses
function createOfflineResponse(request) {
  if (request.headers.get('accept').includes('text/html')) {
    return new Response(
      '<html><body><h1>Offline</h1><p>You are currently offline. Please check your connection.</p></body></html>',
      { headers: { 'Content-Type': 'text/html' } }
    );
  }
  
  return new Response(
    JSON.stringify({ error: 'Offline', message: 'No network connection' }),
    { 
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    }
  );
}

function createAPIFallback(request) {
  const url = new URL(request.url);
  
  if (url.pathname.includes('/weather')) {
    return new Response(
      JSON.stringify({
        success: true,
        data: {
          temperature: 20,
          humidity: 50,
          conditions: 'Clear',
          agricultural_conditions: {
            soil_moisture: 'adequate',
            growing_conditions: 'good',
            recommendation: 'Good conditions for most crops'
          },
          alerts: []
        },
        source: 'offline'
      }),
      { 
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
  
  if (url.pathname.includes('/crop-reports')) {
    return new Response(
      JSON.stringify({
        success: true,
        data: [],
        source: 'offline'
      }),
      { 
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
  
  return createOfflineResponse(request);
}

// Clean expired cache entries
async function cleanExpiredCaches() {
  const cacheNames = [STATIC_CACHE, DYNAMIC_CACHE, API_CACHE];
  
  for (const cacheName of cacheNames) {
    try {
      const cache = await caches.open(cacheName);
      const requests = await cache.keys();
      
      for (const request of requests) {
        const response = await cache.match(request);
        if (response && isExpired(response)) {
          await cache.delete(request);
        }
      }
    } catch (error) {
      console.error('Error cleaning cache:', cacheName, error);
    }
  }
}

// Enhanced sync functions with retry logic
async function syncReports() {
  try {
    const db = await openDB();
    const pendingReports = await db.getAll('pendingReports');
    
    console.log(`Syncing ${pendingReports.length} pending reports`);
    
    for (const report of pendingReports) {
      try {
        const response = await fetch('/api/crop-reports', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(report.data)
        });
        
        if (response.ok) {
          await db.delete('pendingReports', report.id);
          console.log('Successfully synced report:', report.id);
        } else {
          // Mark for retry if server error
          report.retryCount = (report.retryCount || 0) + 1;
          if (report.retryCount < 3) {
            await db.put('pendingReports', report);
          } else {
            await db.delete('pendingReports', report.id);
            console.error('Max retries reached for report:', report.id);
          }
        }
      } catch (error) {
        console.error('Sync error for report:', report.id, error);
        report.retryCount = (report.retryCount || 0) + 1;
        if (report.retryCount < 3) {
          await db.put('pendingReports', report);
        } else {
          await db.delete('pendingReports', report.id);
        }
      }
    }
  } catch (error) {
    console.error('Sync reports error:', error);
  }
}

async function syncWeatherData() {
  try {
    console.log('Syncing weather data cache');
    const cache = await caches.open(API_CACHE);
    
    // Refresh weather data for major cities
    const cities = ['Tashkent', 'Samarkand', 'Bukhara', 'Andijan'];
    
    for (const city of cities) {
      try {
        const response = await fetch(`/api/weather?location=${city}`);
        if (response.ok) {
          await cache.put(`/api/weather?location=${city}`, response.clone());
        }
      } catch (error) {
        console.error(`Error syncing weather for ${city}:`, error);
      }
    }
  } catch (error) {
    console.error('Sync weather data error:', error);
  }
}

async function syncMarketData() {
  try {
    console.log('Syncing market data cache');
    const cache = await caches.open(API_CACHE);
    
    try {
      const response = await fetch('/api/market-prices');
      if (response.ok) {
        await cache.put('/api/market-prices', response.clone());
      }
    } catch (error) {
      console.error('Error syncing market data:', error);
    }
  } catch (error) {
    console.error('Sync market data error:', error);
  }
}

// Store data for background sync
async function storeForSync(data) {
  try {
    const db = await openDB();
    
    if (data.url.includes('/crop-reports')) {
      await db.put('pendingReports', {
        data: JSON.parse(data.body),
        timestamp: data.timestamp,
        retryCount: 0
      });
    }
  } catch (error) {
    console.error('Error storing data for sync:', error);
  }
}

// Enhanced IndexedDB helper with better error handling
function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('agromap-db', 2);
    
    request.onupgradeneeded = event => {
      const db = event.target.result;
      
      // Create object stores if they don't exist
      if (!db.objectStoreNames.contains('pendingReports')) {
        const reportsStore = db.createObjectStore('pendingReports', { 
          keyPath: 'id', 
          autoIncrement: true 
        });
        reportsStore.createIndex('timestamp', 'timestamp', { unique: false });
      }
      
      if (!db.objectStoreNames.contains('weatherCache')) {
        const weatherStore = db.createObjectStore('weatherCache', { 
          keyPath: 'location' 
        });
        weatherStore.createIndex('timestamp', 'timestamp', { unique: false });
      }
      
      if (!db.objectStoreNames.contains('settings')) {
        db.createObjectStore('settings', { keyPath: 'key' });
      }
    };
    
    request.onsuccess = event => {
      const db = event.target.result;
      
      // Add convenience methods
      db.getAll = function(storeName) {
        return new Promise((resolve, reject) => {
          const transaction = this.transaction([storeName], 'readonly');
          const store = transaction.objectStore(storeName);
          const request = store.getAll();
          
          request.onsuccess = () => resolve(request.result);
          request.onerror = () => reject(request.error);
        });
      };
      
      db.put = function(storeName, data) {
        return new Promise((resolve, reject) => {
          const transaction = this.transaction([storeName], 'readwrite');
          const store = transaction.objectStore(storeName);
          const request = store.put(data);
          
          request.onsuccess = () => resolve(request.result);
          request.onerror = () => reject(request.error);
        });
      };
      
      db.delete = function(storeName, key) {
        return new Promise((resolve, reject) => {
          const transaction = this.transaction([storeName], 'readwrite');
          const store = transaction.objectStore(storeName);
          const request = store.delete(key);
          
          request.onsuccess = () => resolve(request.result);
          request.onerror = () => reject(request.error);
        });
      };
      
      resolve(db);
    };
    
    request.onerror = event => reject(event.target.error);
  });
}

// Message handling for communication with main thread
self.addEventListener('message', event => {
  const { type, data } = event.data;
  
  switch (type) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;
      
    case 'GET_CACHE_STATUS':
      getCacheStatus().then(status => {
        event.ports[0].postMessage({ type: 'CACHE_STATUS', data: status });
      });
      break;
      
    case 'CLEAR_CACHE':
      clearAllCaches().then(() => {
        event.ports[0].postMessage({ type: 'CACHE_CLEARED' });
      });
      break;
      
    case 'SYNC_NOW':
      Promise.all([
        syncReports(),
        syncWeatherData(),
        syncMarketData()
      ]).then(() => {
        event.ports[0].postMessage({ type: 'SYNC_COMPLETE' });
      });
      break;
  }
});

// Get cache status
async function getCacheStatus() {
  const cacheNames = await caches.keys();
  const status = {};
  
  for (const name of cacheNames) {
    const cache = await caches.open(name);
    const keys = await cache.keys();
    status[name] = keys.length;
  }
  
  return status;
}

// Clear all caches
async function clearAllCaches() {
  const cacheNames = await caches.keys();
  await Promise.all(cacheNames.map(name => caches.delete(name)));
}

console.log('Service Worker loaded with enhanced caching strategies');