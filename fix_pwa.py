from pathlib import Path

# 1. Popravi api.py da poslužuje service-worker s korijena (/)
api_path = Path("api.py")
api_src = api_path.read_text(encoding="utf-8")

if "@app.route('/service-worker.js')" not in api_src:
    # Dodaj rutu prije glavnog pokretanja
    route_code = """
@app.route('/service-worker.js')
def sw():
    return app.send_static_file('service-worker.js')

if __name__ == "__main__":
"""
    api_src = api_src.replace("if __name__ == \"__main__\":", route_code)
    api_path.write_text(api_src, encoding="utf-8")
    print("✅ api.py: Dodana ruta za /service-worker.js")

# 2. Popravi service-worker.js (dodaj pravi fetch handler)
sw_path = Path("static/service-worker.js")
sw_content = """const CACHE_NAME = 'pallas-v1';

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
"""
sw_path.write_text(sw_content, encoding="utf-8")
print("✅ service-worker.js: Popravljen fetch handler.")

# 3. Popravi index.html da traži SW s korijena (/service-worker.js)
html_path = Path("templates/index.html")
html = html_path.read_text(encoding="utf-8")

# Zamijeni staru putanju (/static/service-worker.js) s novom (/service-worker.js)
html = html.replace("navigator.serviceWorker.register('/static/service-worker.js');", "navigator.serviceWorker.register('/service-worker.js');")

html_path.write_text(html, encoding="utf-8")
print("✅ index.html: Ažurirana putanja do Service Workera.")
print("\nSada pokreni: git add . && git commit -m 'Fix PWA scope' && git push")