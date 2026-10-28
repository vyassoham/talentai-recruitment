"""
TalentAI Enterprise Multi-Tenant Migration Runner
=================================================
Safely applies the Organization and Multi-Tenancy schema migration to Supabase PostgreSQL.
Idempotent, transactional, and updates alembic_version.
"""
import sys
import os
from dotenv import load_dotenv

load_dotenv(r'D:\recruitment_platform\backend\.env')
sys.path.insert(0, r'D:\recruitment_platform\backend')

from sqlalchemy import text
from core.database import SessionLocal

def run_migration():
    print("=" * 70)
    print("TALENTAI ENTERPRISE MULTI-TENANT ISOLATION MIGRATION")
    print("=" * 70)
    
    db = SessionLocal()
    try:
        # 1. Create organizations table
        print("[1/5] Creating 'organizations' table...")
        db.execute(text("""
        CREATE TABLE IF NOT EXISTS organizations (
            id VARCHAR(64) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            slug VARCHAR(128) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS ix_organizations_id ON organizations (id);
        CREATE UNIQUE INDEX IF NOT EXISTS ix_organizations_slug ON organizations (slug);
        """))
        db.commit()

        # 2. Seed Default Organization
        print("[2/5] Seeding Default Enterprise Organization...")
        db.execute(text("""
        INSERT INTO organizations (id, name, slug, is_active)
        VALUES ('org_talentai_default', 'TalentAI Enterprise (Default)', 'talentai-default', true)
        ON CONFLICT (id) DO NOTHING;
        """))
        db.commit()

        # 3. Add organization_id columns and foreign keys
        print("[3/5] Adding organization_id columns and indexes...")
        db.execute(text("""
        -- Users
        ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS organization_id VARCHAR(64) REFERENCES organizations(id) ON DELETE SET NULL;
        CREATE INDEX IF NOT EXISTS ix_users_organization_id ON users (organization_id);

        -- Candidates
        ALTER TABLE candidates 
            ADD COLUMN IF NOT EXISTS organization_id VARCHAR(64) REFERENCES organizations(id) ON DELETE CASCADE;
        CREATE INDEX IF NOT EXISTS ix_candidates_organization_id ON candidates (organization_id);

        -- Job Requirements
        ALTER TABLE job_requirements 
            ADD COLUMN IF NOT EXISTS organization_id VARCHAR(64) REFERENCES organizations(id) ON DELETE CASCADE;
        CREATE INDEX IF NOT EXISTS ix_job_requirements_organization_id ON job_requirements (organization_id);

        -- Recruiter Feedback
        ALTER TABLE recruiter_feedback 
            ADD COLUMN IF NOT EXISTS organization_id VARCHAR(64) REFERENCES organizations(id) ON DELETE CASCADE;
        CREATE INDEX IF NOT EXISTS ix_recruiter_feedback_organization_id ON recruiter_feedback (organization_id);
        """))
        db.commit()

        # 4. Backfill existing records to default organization
        print("[4/5] Backfilling existing records to 'org_talentai_default'...")
        res_users = db.execute(text("UPDATE users SET organization_id = 'org_talentai_default' WHERE organization_id IS NULL;"))
        res_cands = db.execute(text("UPDATE candidates SET organization_id = 'org_talentai_default' WHERE organization_id IS NULL;"))
        res_jobs = db.execute(text("UPDATE job_requirements SET organization_id = 'org_talentai_default' WHERE organization_id IS NULL;"))
        res_fb = db.execute(text("UPDATE recruiter_feedback SET organization_id = 'org_talentai_default' WHERE organization_id IS NULL;"))
        db.commit()
        
        print(f"      Backfilled {res_users.rowcount} users, {res_cands.rowcount} candidates, {res_jobs.rowcount} jobs, {res_fb.rowcount} feedback items.")

        # 5. Update alembic_version
        print("[5/5] Updating alembic_version table to 'e101_multitenant_orgs'...")
        db.execute(text("UPDATE alembic_version SET version_num = 'e101_multitenant_orgs';"))
        db.commit()

        print("=" * 70)
        print("MIGRATION COMPLETED SUCCESSFULLY! MULTI-TENANT SCHEMA IS LIVE.")
        print("=" * 70)
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Migration failed: {e}")
        raise
    finally:
        db.close()

if __name__ == '__main__':
    run_migration()
