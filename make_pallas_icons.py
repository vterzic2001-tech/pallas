from PIL import Image
from pathlib import Path

# Otvori glavnu sliku mudraca
img_path = Path("static/avatars/male.jpg")
if not img_path.exists():
    print("❌ Greška: Ne mogu naći sliku mudraca na putanji static/avatars/male.jpg")
else:
    img = Image.open(img_path)
    
    # 1. Napravi ikonu 192x192
    img_192 = img.resize((192, 192), Image.Resampling.LANCZOS)
    img_192.save("static/icon-192.png", format="PNG")
    print("✅ Stvorena ikona: static/icon-192.png (tvoj mudrac)")

    # 2. Napravi ikonu 512x512
    img_512 = img.resize((512, 512), Image.Resampling.LANCZOS)
    img_512.save("static/icon-512.png", format="PNG")
    print("✅ Stvorena ikona: static/icon-512.png (tvoj mudrac)")