from pathlib import Path

# 1. Kreiraj manifest.json
manifest = '''{
  "name": "PALLAS Cognitive Trainer",
  "short_name": "PALLAS",
  "description": "AI-powered cognitive trainer.",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#f7f8fa",
  "theme_color": "#ec4899",
  "icons": [
    {
      "src": "/static/avatars/male.jpg",
      "sizes": "192x192",
      "type": "image/jpeg",
      "purpose": "any maskable"
    },
    {
      "src": "/static/avatars/male_happy.jpg",
      "sizes": "512x512",
      "type": "image/jpeg",
      "purpose": "any maskable"
    }
  ]
}'''
Path("static/manifest.json").write_text(manifest, encoding="utf-8")

# 2. Kreiraj service-worker.js
sw = '''const CACHE_NAME = 'pallas-v1';
self.addEventListener('install', (event) => { self.skipWaiting(); });
self.addEventListener('activate', (event) => { event.waitUntil(clients.claim()); });
self.addEventListener('fetch', (event) => { });'''
Path("static/service-worker.js").write_text(sw, encoding="utf-8")

# 3. Uredi index.html
html_path = Path("templates/index.html")
html = html_path.read_text(encoding="utf-8")

if 'rel="manifest"' not in html:
    html = html.replace('<title>', '<link rel="manifest" href="/static/manifest.json">\n    <meta name="theme-color" content="#ec4899">\n    <title>')

if 'service-worker.js' not in html:
    sw_script = '''<script>
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/service-worker.js');
  }
</script>
</body>'''
    html = html.replace('</body>', sw_script)

html_path.write_text(html, encoding="utf-8")
print("✅ PWA datoteke stvorene i HTML ažuriran!")