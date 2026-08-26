from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import router as root_router
from api.routes import router as cv_router
from api.routes_jobs import router as jobs_router
from api.routes_search import router as search_router
from api.routes_analytics import router as analytics_router
from api.routes_sourcing import router as sourcing_router
from api.routes_count import router as count_router
from api.routes_auth import router as auth_router
from core.database import engine, Base
from core.config import settings
from core.logging_middleware import CorrelationIDMiddleware, setup_structured_logging
from models import all_models 

# Configure structured logging
setup_structured_logging()

app = FastAPI(
    title="AI Recruitment Platform MVP",
    description="Enterprise Intelligent Candidate Matching, Screening & Sourcing Platform",
    version="0.1.0"
)

# Attach Correlation ID and Structured Logging Middleware
app.add_middleware(CorrelationIDMiddleware)

# Attach CORS Middleware with validated settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(root_router, prefix="/api/v1")
app.include_router(cv_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(sourcing_router, prefix="/api/v1")
app.include_router(count_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])

@app.get("/health")
def health_check():
    return {"status": "ok", "provider": settings.AI_PROVIDER, "queue": settings.QUEUE_BACKEND}
