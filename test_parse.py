import requests
import json

base_url = "https://talentai-recruitment.onrender.com/api/v1"

# 1. Login
resp = requests.post(f"{base_url}/auth/token", data={
    "username": "admin@recruit.ai",
    "password": "admin_password"
})
if resp.status_code != 200:
    print(f"Login failed: {resp.status_code} {resp.text}")
    exit(1)

token = resp.json().get("access_token")

# 2. Parse Job
req_body = {
    "job_description": "We are looking for a Lead AI & Distributed Systems Architect to scale our talent intelligence platform. Mandatory Qualifications: - 5+ years of experience with Python, FastAPI, and PostgreSQL with pgvector",
    "title": "Lead AI & Distributed Systems Architect",
    "min_experience_years": 5
}

resp = requests.post(
    f"{base_url}/jobs/parse",
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    json=req_body,
    timeout=60
)

print(resp.status_code)
print(resp.text)
