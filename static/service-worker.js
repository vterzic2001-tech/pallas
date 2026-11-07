const CACHE_NAME = 'pallas-v1';

self.addEventListener('install', (event) => {
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(clients.claim());
});

self.addEventListener('fetch', (event) => {
    // Samo proslijedi zahtjev dalje (mreža). 
    // Ovo je dovoljno da preglednik dopusti instalaciju.
    event.respondWith(fetch(event.request));
});
