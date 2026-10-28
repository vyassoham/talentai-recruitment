import os
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
from core.database import engine, Base, SessionLocal
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
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "https://talentai-recruiter.vercel.app"] + [url.strip() for url in os.getenv("FRONTEND_URL", "").split(",") if url.strip() and url.strip() != "*"],
    allow_origin_regex=r'https://.*\.vercel\.app',
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(root_router, prefix="/api/v1")
app.include_router(count_router, prefix="/api/v1")
app.include_router(cv_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(sourcing_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])

@app.on_event("startup")
def on_startup():
    """Ensure database tables, vector extension, and default admin exist on startup."""
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
    except Exception:
        pass

    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass

    try:
        from core.auth import AuthUtils
        from models.all_models import User, UserRole
        db = SessionLocal()
        admin = db.query(User).filter(User.email == "admin@recruit.ai").first()
        if not admin:
            admin = User(
                email="admin@recruit.ai",
                hashed_password=AuthUtils.get_password_hash("admin_password"),
                role=UserRole.ADMIN.value,
                is_active=True
            )
            db.add(admin)
            db.commit()
        db.close()
    except Exception:
        pass

    try:
        from core.queue import queue_client
        if hasattr(queue_client, "start_worker"):
            queue_client.start_worker()
    except Exception as e:
        pass

@app.on_event("shutdown")
def on_shutdown():
    try:
        from core.queue import queue_client
        if hasattr(queue_client, "stop_worker"):
            queue_client.stop_worker()
    except Exception:
        pass

@app.get("/health")
@app.get("/api/v1/health")
def health_check():
    return {"status": "ok", "provider": settings.AI_PROVIDER, "queue": settings.QUEUE_BACKEND}
