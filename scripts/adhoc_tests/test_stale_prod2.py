import requests

url = 'https://talentai-recruitment.onrender.com/api/v1/sourcing/stale-profiles'
try:
    resp = requests.get(url, timeout=30)
    print("STATUS:", resp.status_code)
    print("RESPONSE:", resp.text[:500])
except Exception as e:
    print("ERROR:", e)
