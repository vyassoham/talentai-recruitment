import requests
from backend.core.config import settings
import json
from services.documents.schemas import StructuredCandidate

schema_json = StructuredCandidate.model_json_schema()
sys_prompt = '''You are an expert recruitment AI. Extract candidate information from the provided text into the strict JSON schema.
Rules:
1. Extract explicit facts only. Do not hallucinate.
2. Format dates as YYYY-MM where possible, or 'present' if current.
3. For 'evidence' in skills, provide the exact quote from the CV mentioning it.
4. If a field is not found, leave it null.

You MUST output strictly valid JSON conforming to this JSON Schema:
''' + json.dumps(schema_json)

url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={settings.GEMINI_API_KEY}'
payload = {
    'contents': [
        {
            'role': 'user',
            'parts': [{'text': f'System Context:\n{sys_prompt}\n\nUser Request:\nJAGDISH PRAJAPATI\nEmail: jagdish.prajapati@gmail.com\nPhone: +91 9876543210'}]
        }
    ],
    'generationConfig': {
        'responseMimeType': 'application/json',
        'temperature': 0.1
    }
}
resp = requests.post(url, json=payload)
print(resp.json())
