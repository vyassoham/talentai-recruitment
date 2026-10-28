from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from core.auth import require_role
from models.all_models import Candidate, User

router = APIRouter()

@router.get("/candidates/count")
def get_candidate_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("RECRUITER"))
):
    count = db.query(Candidate).count()
    return {"total_amount": count}
