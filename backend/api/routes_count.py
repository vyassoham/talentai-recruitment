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
    """
    Returns candidate count segregated by tenant organization.
    Enterprise tenant recruiters see only candidates belonging to their organization.
    """
    query = db.query(Candidate)
    if current_user.role != "ADMIN" and current_user.organization_id:
        query = query.filter(Candidate.organization_id == current_user.organization_id)
    count = query.count()
    return {"total_amount": count}
