from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from models.all_models import Candidate

router = APIRouter()

@router.get("/candidates/count")
def get_candidate_count(db: Session = Depends(get_db)):
    count = db.query(Candidate).count()
    return {"total_amount": count}
