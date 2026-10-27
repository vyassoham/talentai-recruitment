import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from core.database import SessionLocal
from api.routes_search import SearchRequest, search_candidates
from models.all_models import JobRequirement

async def test_search():
    db = SessionLocal()
    req = SearchRequest(
        job_id="1",
        query="Frontend React developer with Next.js 14 and Tailwind",
        top_k=5
    )
    res = await search_candidates(req, db, None, None)
    print("Retrieved Count:", res['retrieved_count'])
    for idx, c in enumerate(res['candidates'][:5]):
        print(f"#{idx+1} {c['name']} - Score: {c['retrieval_score']}")
        print("AI Match Score:", c.get('match_score'))
        print("Reasons:", c.get('match_reasons'))

asyncio.run(test_search())
