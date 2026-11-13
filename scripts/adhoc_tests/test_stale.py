from backend.api.routes_sourcing import get_stale_profiles
from core.database import SessionLocal
from models.all_models import User
db = SessionLocal()
try:
    print(get_stale_profiles(threshold_days=90, limit=50, current_user=User(id='test', role='RECRUITER')))
except Exception as e:
    print('ERROR:', e)
