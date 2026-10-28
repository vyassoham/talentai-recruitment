import requests
import re

url = "https://talentai-recruiter.vercel.app"
r = requests.get(url, timeout=15)
scripts = re.findall(r'src="(/_next/static/[^"]+\.js)"', r.text)
print(f"Found {len(scripts)} static scripts on Vercel.")

found_backends = set()
for s in scripts:
    js_url = url + s
    r_js = requests.get(js_url, timeout=15)
    backends = re.findall(r'https://[a-zA-Z0-9\.-]+onrender\.com[a-zA-Z0-9_\/]*', r_js.text)
    for b in backends:
        found_backends.add(b)

print("Backend endpoints referenced in Vercel bundle:", found_backends)
