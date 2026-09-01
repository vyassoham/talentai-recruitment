from core.database import SessionLocal
from models.all_models import JobRequirement
from backend.api.routes_search import SearchRequest
from backend.api.routes_search import search_candidates
import asyncio

async def test_search():
    db = SessionLocal()
    req = SearchRequest(
        job_id="1",
        query="Senior ML Engineer with PyTorch & pgvector experience",
        top_k=20
    )
    # mock current_user and rate_limit
    res = await search_candidates(req, db, None, None)
    print("Retrieved Count:", res['retrieved_count'])
    for idx, c in enumerate(res['candidates'][:5]):
        print(f"#{idx+1} {c['name']} - Score: {c['retrieval_score']} - Exp: {c['total_experience_years']}")

asyncio.run(test_search())
