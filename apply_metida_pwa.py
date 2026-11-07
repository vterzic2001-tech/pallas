from pathlib import Path
import re

# 1. Manifest.json (PALLAS verzija)
manifest = '''{
  "name": "PALLAS",
  "short_name": "PALLAS",
  "description": "AI Cognitive Trainer",
  "start_url": "/",
  "display": "standalone",
  "orientation": "portrait",
  "background_color": "#ec4899",
  "theme_color": "#ec4899",
  "lang": "en",
  "icons": [
    {
      "src": "/static/icon-192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/static/icon-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any maskable"
    }
  ]
}'''
Path("static/manifest.json").write_text(manifest, encoding="utf-8")

# 2. Service Worker (Metidin provjereni kod)
sw = '''const CACHE_NAME = 'pallas-v1';
const ASSETS = ['/', '/static/manifest.json'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

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

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  if (url.pathname.startsWith('/api/')) {
    event.respondWith(fetch(event.request));
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response.status === 200 && event.request.method === 'GET') {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});'''
Path("static/service-worker.js").write_text(sw, encoding="utf-8")

# 3. api.py ruta za SW
api_path = Path("api.py")
api_src = api_path.read_text(encoding="utf-8")
if "@app.route('/service-worker.js')" not in api_src:
    route_code = """
@app.route('/service-worker.js')
def sw():
    return app.send_static_file('service-worker.js')

if __name__ == "__main__":
"""
    api_src = api_src.replace('if __name__ == "__main__":', route_code)
    api_path.write_text(api_src, encoding="utf-8")

# 4. index.html tagovi
html_path = Path("templates/index.html")
html = html_path.read_text(encoding="utf-8")

html = re.sub(r'<link rel="manifest".*?>', '', html)
html = re.sub(r'<link rel="apple-touch-icon".*?>', '', html)
html = re.sub(r'<meta name="theme-color".*?>', '', html)
html = re.sub(r'<meta name="apple-mobile-web-app.*?>', '', html)

head_tags = '''<link rel="manifest" href="/static/manifest.json">
    <meta name="theme-color" content="#ec4899">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <link rel="apple-touch-icon" href="/static/icon-192.png">
    <title>PALLAS - Cognitive Trainer</title>'''

html = html.replace('<title>PALLAS - Cognitive Trainer</title>', head_tags)
html_path.write_text(html, encoding="utf-8")

print("✅ PWA je u potpunosti postavljen s PALLAS ikonama!")