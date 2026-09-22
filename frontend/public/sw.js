const CACHE_NAME = 'skysafe-v1';
const STATIC_ASSETS = [
  '/',
  '/chat',
  '/dashboard',
  '/citizen',
  '/manifest.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.filter(name => name !== CACHE_NAME).map(name => caches.delete(name))
      );
    })
  );
  self.clients.claim();
});

// IndexedDB Helper
const DB_NAME = 'SkySafeDB';
const DB_VERSION = 1;

function getDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains('outbox')) {
        db.createObjectStore('outbox', { keyPath: 'id', autoIncrement: true });
      }
      if (!db.objectStoreNames.contains('cache')) {
        db.createObjectStore('cache', { keyPath: 'key' });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function saveToOutbox(url, options) {
  const db = await getDB();
  const tx = db.transaction('outbox', 'readwrite');
  tx.objectStore('outbox').add({
    url,
    method: options.method,
    headers: options.headers,
    body: options.body,
    timestamp: Date.now()
  });
  return tx.complete;
}

async function syncOutbox() {
  const db = await getDB();
  const tx = db.transaction('outbox', 'readonly');
  const store = tx.objectStore('outbox');
  const items = await new Promise(res => {
    const req = store.getAll();
    req.onsuccess = () => res(req.result);
  });

  if (items.length === 0) return;

  console.log(`[SW] Syncing ${items.length} outbox items`);
  for (const item of items) {
    try {
      await fetch(item.url, {
        method: item.method,
        headers: item.headers,
        body: item.body
      });
      // On success, delete from outbox
      const delTx = db.transaction('outbox', 'readwrite');
      delTx.objectStore('outbox').delete(item.id);
      await delTx.complete;
    } catch (err) {
      console.error('[SW] Sync failed for item', item, err);
      // Stop syncing if we hit a network error again
      break;
    }
  }
}

self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-outbox') {
    event.waitUntil(syncOutbox());
  }
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Intercept API calls to queue them if offline
  if (url.pathname === '/api/reports' && event.request.method === 'POST') {
    if (!navigator.onLine) {
      // Offline: queue it
      event.respondWith((async () => {
        const cloned = event.request.clone();
        const body = await cloned.text();
        const headers = {};
        for (const [k, v] of cloned.headers.entries()) {
          headers[k] = v;
        }
        await saveToOutbox(cloned.url, {
          method: cloned.method,
          headers,
          body
        });
        
        // Try registering sync if supported
        if ('sync' in self.registration) {
          try { await self.registration.sync.register('sync-outbox'); } catch(e){}
        }

        return new Response(JSON.stringify({ status: "queued", message: "Offline: Report queued for sync." }), {
          headers: { 'Content-Type': 'application/json' }
        });
      })());
      return;
    }
  }

  // Caching strategy for API /alerts, /decision/state, /chat (only GETs)
  if (url.pathname.startsWith('/api/') && event.request.method === 'GET') {
    event.respondWith(
      fetch(event.request)
        .then(async (response) => {
          const clone = response.clone();
          const db = await getDB();
          const tx = db.transaction('cache', 'readwrite');
          const data = await clone.json();
          tx.objectStore('cache').put({ key: url.pathname, data, timestamp: Date.now() });
          return response;
        })
        .catch(async () => {
          // Offline fallback from IndexedDB cache
          const db = await getDB();
          return new Promise((resolve) => {
            const tx = db.transaction('cache', 'readonly');
            const req = tx.objectStore('cache').get(url.pathname);
            req.onsuccess = () => {
              if (req.result) {
                resolve(new Response(JSON.stringify(req.result.data), {
                  headers: { 'Content-Type': 'application/json' }
                }));
              } else {
                resolve(new Response(JSON.stringify({ error: "Offline and no cached data available." }), {
                  status: 503, headers: { 'Content-Type': 'application/json' }
                }));
              }
            };
          });
        })
    );
    return;
  }

  // Standard Stale-While-Revalidate for app shell/assets
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      const networkFetch = fetch(event.request).then((response) => {
        if (event.request.method === 'GET' && response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      }).catch(() => {
        // Ignored, we just return cache if fetch fails
      });
      return cachedResponse || networkFetch;
    })
  );
});
