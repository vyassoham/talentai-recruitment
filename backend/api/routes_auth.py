import json
import urllib.parse
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from core.database import get_db
from models.all_models import User, UserRole
from core.auth import AuthUtils, ACCESS_TOKEN_EXPIRE_MINUTES
from core.config import settings
from core.rate_limiter import rate_limit

router = APIRouter()

class Token(BaseModel):
    access_token: str
    token_type: str

class SeedAdminResponse(BaseModel):
    message: str
    email: str
    password: str

@router.post("/token", response_model=Token)
async def login_for_access_token(
    request: Request,
    db: Session = Depends(get_db),
    _rate_check = Depends(rate_limit(max_requests=20, window_seconds=60))
):
    """
    Robust OAuth2 Password exchange endpoint.
    Accepts:
    1. Standard form-urlencoded OAuth2 username & password
    2. JSON payload {"username": "...", "password": "..."} or {"email": "...", "password": "..."}
    3. URL-encoded payload sent with application/json header (recovers legacy web bundles)
    """
    username = None
    password = None

    raw_body = await request.body()
    raw_text = raw_body.decode("utf-8", errors="ignore").strip()

    # 1. Try JSON parsing
    if raw_text.startswith("{") and raw_text.endswith("}"):
        try:
            body_json = json.loads(raw_text)
            if isinstance(body_json, dict):
                username = body_json.get("username") or body_json.get("email")
                password = body_json.get("password")
        except Exception:
            pass

    # 2. Try URL-encoded / Form parsing
    if not username or not password:
        try:
            parsed = urllib.parse.parse_qs(raw_text)
            if "username" in parsed and parsed["username"]:
                username = parsed["username"][0]
            elif "email" in parsed and parsed["email"]:
                username = parsed["email"][0]
            if "password" in parsed and parsed["password"]:
                password = parsed["password"][0]
        except Exception:
            pass

    # 3. Fallback to standard FastAPI request.form()
    if not username or not password:
        try:
            form = await request.form()
            username = form.get("username") or form.get("email")
            password = form.get("password")
        except Exception:
            pass

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.email == username).first()
    if not user or not AuthUtils.verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = AuthUtils.create_access_token(
        data={"sub": user.email, "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/seed-admin", response_model=SeedAdminResponse)
def seed_admin_user(
    db: Session = Depends(get_db),
    _rate_check = Depends(rate_limit(max_requests=3, window_seconds=60))
):
    """
    Creates a default admin user if no users exist. 
    Strictly disabled in production environments to prevent unauthorized account creation.
    """
    if settings.ENVIRONMENT == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Admin account seeding is disabled in production environments."
        )

    if db.query(User).first():
        raise HTTPException(status_code=400, detail="Users already exist. Cannot seed.")
        
    admin_email = "admin@recruit.ai"
    admin_password = "admin_password"
    
    hashed = AuthUtils.get_password_hash(admin_password)
    user = User(email=admin_email, hashed_password=hashed, role=UserRole.ADMIN.value)
    db.add(user)
    db.commit()
    
    return {"message": "Admin user created successfully", "email": admin_email, "password": admin_password}
