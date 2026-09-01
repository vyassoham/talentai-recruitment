import requests
import json

url = 'http://127.0.0.1:8000/api/v1/jobs/parse'
data = {
    'job_description': 'Looking for a Python dev',
    'title': 'Dev',
    'min_experience_years': 2.0
}
try:
    resp = requests.post(url, json=data, timeout=30)
    print("STATUS:", resp.status_code)
    print("RESPONSE:", resp.text)
except Exception as e:
    print("ERROR:", e)
