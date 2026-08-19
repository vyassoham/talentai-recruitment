from fastapi import APIRouter

router = APIRouter()

# Example routes (to be implemented)
# router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
# router.include_router(candidates.router, prefix="/candidates", tags=["candidates"])

@router.get("/")
def read_root():
    return {"message": "API is running"}
