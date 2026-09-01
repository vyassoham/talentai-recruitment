import requests
import json

url = 'https://talentai-recruitment.onrender.com/api/v1/jobs/parse'
data = {
    'job_description': 'Looking for a Python dev',
    'title': 'Dev',
    'min_experience_years': 2.0
}
# Need a valid token! We'll just test if we get 401 or a crash
try:
    resp = requests.post(url, json=data, timeout=30)
    print("STATUS:", resp.status_code)
    print("RESPONSE:", resp.text)
except Exception as e:
    print("ERROR:", e)
