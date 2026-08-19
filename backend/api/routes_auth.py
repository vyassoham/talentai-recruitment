from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
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
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db),
    _rate_check = Depends(rate_limit(max_requests=10, window_seconds=60))
):
    """
    OAuth2 Password exchange endpoint protected with brute-force rate limiting.
    """
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not AuthUtils.verify_password(form_data.password, user.hashed_password):
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
