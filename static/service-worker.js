const CACHE = 'field-hub-v3-no-login';
const ASSETS = ['/', '/static/css/style.css', '/static/js/app.js', '/static/manifest.json'];
self.addEventListener('install', event => event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS))));
self.addEventListener('fetch', event => event.respondWith(caches.match(event.request).then(response => response || fetch(event.request))));
