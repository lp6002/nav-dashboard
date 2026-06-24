import urllib.request
import os
import time

save_dir = r"C:\Users\lp263\工作空间\导航页\icons"
os.makedirs(save_dir, exist_ok=True)

domains = [
    "appsflyer.com",
    "mintegral.com",
    "unity.com",
    "analytics.google.com",
    "handbrake.fr",
    "mojie.app",
    "holopix.cn",
    "frameronin.com",
    "tiktok.com",
    "youtube.com",
    "facebook.com",
    "instagram.com",
    "figma.com",
    "canva.com",
    "unsplash.com",
    "remove.bg",
    "notion.so",
    "docs.google.com",
    "sheets.google.com",
    "trello.com",
    "github.com",
]

for domain in domains:
    url = f"https://www.google.com/s2/favicons?domain={domain}&sz=64"
    path = os.path.join(save_dir, f"{domain}.ico")
    if os.path.exists(path):
        print(f"skip {domain}")
        continue
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
        with open(path, "wb") as f:
            f.write(data)
        print(f"ok {domain} ({len(data)} bytes)")
    except Exception as e:
        print(f"fail {domain}: {e}")
    time.sleep(0.1)

print("done")
