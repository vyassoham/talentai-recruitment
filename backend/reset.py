from sqlalchemy import text
from core.database import SessionLocal
db = SessionLocal()
db.execute(text("SELECT setval(pg_get_serial_sequence('job_requirements', 'id'), coalesce(max(id), 0) + 1, false) FROM job_requirements;"))
db.commit()
print('Sequence reset!')
