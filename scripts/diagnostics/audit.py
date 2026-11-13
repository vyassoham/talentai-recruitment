import requests
import json

BASE = 'https://talentai-recruitment.onrender.com/api/v1'

def get_token():
    resp = requests.post(f'{BASE}/auth/token', data={'username':'admin@recruit.ai', 'password':'admin_password'})
    return resp.json().get('access_token')

token = get_token()
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

def test(name, method, url, **kwargs):
    print(f'Testing {name}...')
    try:
        if method == 'GET':
            r = requests.get(f'{BASE}{url}', headers=headers, timeout=20)
        else:
            r = requests.post(f'{BASE}{url}', headers=headers, **kwargs, timeout=30)
        
        if r.status_code == 200:
            print(f'[SUCCESS] {name} (200 OK)')
        else:
            print(f'[FAILED] {name} ({r.status_code}): {r.text}')
    except Exception as e:
        print(f'[ERROR] {name}: {e}')

# 1. Parse Job
test('Parse Job', 'POST', '/jobs/parse', json={'raw_description': 'Test Python Dev', 'title': 'Test Job', 'min_experience_years': 2.0})

# 2. Candidate Detail
test('Candidate Detail', 'GET', '/candidates/1')

# 3. Telemetry
test('Telemetry Analytics', 'GET', '/analytics/cost')

# 4. DEI Analytics
test('DEI Analytics', 'GET', '/analytics/dei?job_id=1&threshold=0.5')

