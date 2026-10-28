import sys
from dotenv import load_dotenv

load_dotenv(r'D:\recruitment_platform\backend\.env')
sys.path.insert(0, r'D:\recruitment_platform\backend')

from core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

print("=" * 70)
print("SUPABASE POSTGRESQL RLS & DATABASE ROLE PERMISSIONS AUDIT")
print("=" * 70)

user_info = db.execute(text("SELECT current_user, session_user, current_database();")).fetchall()
print(f"Connection Identity: {user_info}")

rls_info = db.execute(text("""
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
  AND tablename IN ('candidates', 'job_requirements', 'organizations', 'recruiter_feedback', 'candidate_documents', 'users')
ORDER BY tablename;
""")).fetchall()

print("\nTable Row-Level Security (RLS) Status:")
for t, rls in rls_info:
    print(f"  - {t:<25}: RLS = {rls}")

role_attrs = db.execute(text("""
SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolcanlogin, rolreplication, rolbypassrls
FROM pg_roles
WHERE rolname = CURRENT_USER;
""")).fetchall()

print(f"\nRole Attributes for current connection role:")
for r in role_attrs:
    print(f"  Role: {r[0]} | Superuser: {r[1]} | BypassRLS: {r[6]} | CanLogin: {r[4]}")

policies = db.execute(text("""
SELECT tablename, policyname, permissive, roles, cmd, qual, with_check
FROM pg_policies
WHERE schemaname = 'public';
""")).fetchall()

print(f"\nConfigured pg_policies count: {len(policies)}")
for p in policies:
    print(f"  Table: {p[0]} | Policy: {p[1]} | Cmd: {p[4]}")

print("=" * 70)
db.close()
