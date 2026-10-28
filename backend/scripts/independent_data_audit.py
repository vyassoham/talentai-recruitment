import os
import sys
from dotenv import load_dotenv

load_dotenv(r'D:\recruitment_platform\backend\.env')
sys.path.insert(0, r'D:\recruitment_platform\backend')

from sqlalchemy import text
from core.database import SessionLocal

db = SessionLocal()

print("=" * 70)
print("INDEPENDENT DATA INTEGRITY & AUDIT VERIFICATION")
print("=" * 70)

# 1. Candidate Name Repair
total_cands = db.execute(text("SELECT COUNT(*) FROM candidates")).scalar()
backup_rows = db.execute(text("SELECT COUNT(*) FROM candidate_name_backup_20261028")).scalar()
sample_repairs = db.execute(text("SELECT candidate_id, original_name, repaired_name, confidence FROM candidate_name_backup_20261028 LIMIT 5")).fetchall()

print(f"[1] Candidate Name Audit:")
print(f"    Total candidates: {total_cands}")
print(f"    Backup table (candidate_name_backup_20261028) rows: {backup_rows}")
print(f"    Sample verified repairs:")
for r in sample_repairs:
    # Check current name in candidates table
    curr_name = db.execute(text(f"SELECT name FROM candidates WHERE id = {r[0]}")).scalar()
    print(f"      ID {r[0]}: '{r[1]}' -> '{r[2]}' (Current in DB: '{curr_name}', Conf: {r[3]})")

# 2. Multi-Tenant Organization Backfill
print(f"\n[2] Multi-Tenant Schema & Backfill Audit:")
orgs = db.execute(text("SELECT id, name, slug, is_active FROM organizations")).fetchall()
print(f"    Organizations present: {orgs}")
cands_with_org = db.execute(text("SELECT COUNT(*) FROM candidates WHERE organization_id = 'org_talentai_default'")).scalar()
cands_null_org = db.execute(text("SELECT COUNT(*) FROM candidates WHERE organization_id IS NULL")).scalar()
users_with_org = db.execute(text("SELECT COUNT(*) FROM users WHERE organization_id = 'org_talentai_default'")).scalar()
jobs_with_org = db.execute(text("SELECT COUNT(*) FROM job_requirements WHERE organization_id = 'org_talentai_default'")).scalar()

print(f"    Candidates assigned to default tenant: {cands_with_org} (NULL: {cands_null_org})")
print(f"    Users assigned to default tenant:      {users_with_org}")
print(f"    Jobs assigned to default tenant:       {jobs_with_org}")

# 3. Vector Embeddings
print(f"\n[3] Vector Embedding Coverage & Dimensionality Audit:")
embedded_count = db.execute(text("SELECT COUNT(*) FROM candidates WHERE embedding IS NOT NULL")).scalar()
null_embedding_count = total_cands - embedded_count
section_embeddings_count = db.execute(text("SELECT COUNT(*) FROM candidate_section_embeddings")).scalar()

print(f"    Candidates with 1536-d global embeddings: {embedded_count} / {total_cands} ({embedded_count/total_cands*100:.2f}%)")
print(f"    Candidates awaiting embeddings:          {null_embedding_count}")
print(f"    Multi-vector chunked section embeddings: {section_embeddings_count}")

# 4. Resume Documents
print(f"\n[4] Candidate Documents Audit:")
total_docs = db.execute(text("SELECT COUNT(*) FROM candidate_documents")).scalar()
docs_with_key = db.execute(text("SELECT COUNT(*) FROM candidate_documents WHERE storage_key IS NOT NULL")).scalar()
docs_with_hash = db.execute(text("SELECT COUNT(*) FROM candidate_documents WHERE sha256_hash IS NOT NULL")).scalar()
print(f"    Total document records: {total_docs}")
print(f"    Documents with storage_key: {docs_with_key}")
print(f"    Documents with sha256_hash: {docs_with_hash}")

print("=" * 70)
db.close()
