"""
apply_supabase_rls_policies.py
==============================
Applies production-grade PostgreSQL Row-Level Security (RLS) policies
and role grants to Supabase tables.

Protects against:
- Data leakage via PostgREST / anon key
- Cross-tenant data tampering by authenticated users
- Demographics / feedback IDOR enumeration
"""
import sys
import os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / '.env')

from core.database import engine
from sqlalchemy import text

POLICIES_SQL = """
-- 1. Helper function for tenant resolution from JWT or session
CREATE OR REPLACE FUNCTION public.current_org_id()
RETURNS text
LANGUAGE sql
STABLE
AS $$
  SELECT COALESCE(
    auth.jwt() ->> 'org_id',
    auth.jwt() ->> 'organization_id',
    auth.jwt() -> 'user_metadata' ->> 'organization_id',
    auth.jwt() -> 'app_metadata' ->> 'organization_id',
    nullif(current_setting('app.current_org_id', true), '')
  );
$$;

GRANT EXECUTE ON FUNCTION public.current_org_id() TO authenticated, anon, service_role, postgres;

-- 2. Sequence permissions for authenticated users
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE, TRIGGER, REFERENCES ON ALL TABLES IN SCHEMA public FROM anon;

-- 3. Enable RLS on core tables
ALTER TABLE public.candidates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.job_requirements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.recruiter_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.candidate_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.candidate_demographics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.candidate_skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.candidate_section_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.employment ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evaluation_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ingestion_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.background_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ontology ENABLE ROW LEVEL SECURITY;

-- 4. Clean up any preexisting policies to prevent duplicate policy errors
DROP POLICY IF EXISTS candidates_tenant_isolation ON public.candidates;
DROP POLICY IF EXISTS job_requirements_tenant_isolation ON public.job_requirements;
DROP POLICY IF EXISTS recruiter_feedback_tenant_isolation ON public.recruiter_feedback;
DROP POLICY IF EXISTS organizations_tenant_isolation ON public.organizations;
DROP POLICY IF EXISTS users_tenant_isolation ON public.users;
DROP POLICY IF EXISTS candidate_documents_tenant_isolation ON public.candidate_documents;
DROP POLICY IF EXISTS candidate_demographics_tenant_isolation ON public.candidate_demographics;
DROP POLICY IF EXISTS candidate_skills_tenant_isolation ON public.candidate_skills;
DROP POLICY IF EXISTS candidate_section_embeddings_tenant_isolation ON public.candidate_section_embeddings;
DROP POLICY IF EXISTS employment_tenant_isolation ON public.employment;
DROP POLICY IF EXISTS evaluation_evidence_tenant_isolation ON public.evaluation_evidence;
DROP POLICY IF EXISTS ingestion_jobs_tenant_isolation ON public.ingestion_jobs;
DROP POLICY IF EXISTS ontology_read_policy ON public.ontology;

-- 5. Create production RLS policies
CREATE POLICY candidates_tenant_isolation ON public.candidates
  FOR ALL TO authenticated
  USING (organization_id = public.current_org_id())
  WITH CHECK (organization_id = public.current_org_id());

CREATE POLICY job_requirements_tenant_isolation ON public.job_requirements
  FOR ALL TO authenticated
  USING (organization_id = public.current_org_id())
  WITH CHECK (organization_id = public.current_org_id());

CREATE POLICY recruiter_feedback_tenant_isolation ON public.recruiter_feedback
  FOR ALL TO authenticated
  USING (organization_id = public.current_org_id())
  WITH CHECK (organization_id = public.current_org_id());

CREATE POLICY organizations_tenant_isolation ON public.organizations
  FOR SELECT TO authenticated
  USING (id = public.current_org_id());

CREATE POLICY users_tenant_isolation ON public.users
  FOR ALL TO authenticated
  USING (organization_id = public.current_org_id())
  WITH CHECK (organization_id = public.current_org_id());

CREATE POLICY candidate_documents_tenant_isolation ON public.candidate_documents
  FOR ALL TO authenticated
  USING (EXISTS (
    SELECT 1 FROM public.candidates c 
    WHERE c.id = candidate_documents.candidate_id 
      AND c.organization_id = public.current_org_id()
  ))
  WITH CHECK (EXISTS (
    SELECT 1 FROM public.candidates c 
    WHERE c.id = candidate_documents.candidate_id 
      AND c.organization_id = public.current_org_id()
  ));

CREATE POLICY candidate_demographics_tenant_isolation ON public.candidate_demographics
  FOR ALL TO authenticated
  USING (EXISTS (
    SELECT 1 FROM public.candidates c 
    WHERE c.id = candidate_demographics.candidate_id 
      AND c.organization_id = public.current_org_id()
  ))
  WITH CHECK (EXISTS (
    SELECT 1 FROM public.candidates c 
    WHERE c.id = candidate_demographics.candidate_id 
      AND c.organization_id = public.current_org_id()
  ));

CREATE POLICY candidate_skills_tenant_isolation ON public.candidate_skills
  FOR ALL TO authenticated
  USING (EXISTS (
    SELECT 1 FROM public.candidates c 
    WHERE c.id = candidate_skills.candidate_id 
      AND c.organization_id = public.current_org_id()
  ))
  WITH CHECK (EXISTS (
    SELECT 1 FROM public.candidates c 
    WHERE c.id = candidate_skills.candidate_id 
      AND c.organization_id = public.current_org_id()
  ));

CREATE POLICY candidate_section_embeddings_tenant_isolation ON public.candidate_section_embeddings
  FOR ALL TO authenticated
  USING (EXISTS (
    SELECT 1 FROM public.candidates c 
    WHERE c.id = candidate_section_embeddings.candidate_id 
      AND c.organization_id = public.current_org_id()
  ))
  WITH CHECK (EXISTS (
    SELECT 1 FROM public.candidates c 
    WHERE c.id = candidate_section_embeddings.candidate_id 
      AND c.organization_id = public.current_org_id()
  ));

CREATE POLICY employment_tenant_isolation ON public.employment
  FOR ALL TO authenticated
  USING (EXISTS (
    SELECT 1 FROM public.candidates c 
    WHERE c.id = employment.candidate_id 
      AND c.organization_id = public.current_org_id()
  ))
  WITH CHECK (EXISTS (
    SELECT 1 FROM public.candidates c 
    WHERE c.id = employment.candidate_id 
      AND c.organization_id = public.current_org_id()
  ));

CREATE POLICY evaluation_evidence_tenant_isolation ON public.evaluation_evidence
  FOR ALL TO authenticated
  USING (EXISTS (
    SELECT 1 FROM public.candidates c 
    WHERE c.id = evaluation_evidence.candidate_id 
      AND c.organization_id = public.current_org_id()
  ))
  WITH CHECK (EXISTS (
    SELECT 1 FROM public.candidates c 
    WHERE c.id = evaluation_evidence.candidate_id 
      AND c.organization_id = public.current_org_id()
  ));

CREATE POLICY ingestion_jobs_tenant_isolation ON public.ingestion_jobs
  FOR ALL TO authenticated
  USING (EXISTS (
    SELECT 1 FROM public.candidate_documents cd 
    JOIN public.candidates c ON cd.candidate_id = c.id
    WHERE cd.id = ingestion_jobs.document_id 
      AND c.organization_id = public.current_org_id()
  ))
  WITH CHECK (EXISTS (
    SELECT 1 FROM public.candidate_documents cd 
    JOIN public.candidates c ON cd.candidate_id = c.id
    WHERE cd.id = ingestion_jobs.document_id 
      AND c.organization_id = public.current_org_id()
  ));

CREATE POLICY ontology_read_policy ON public.ontology
  FOR SELECT TO authenticated, anon
  USING (true);
"""

def apply_policies():
    print("=" * 70)
    print("APPLYING SUPABASE ROW-LEVEL SECURITY (RLS) POLICIES")
    print("=" * 70)
    
    raw_conn = engine.raw_connection()
    try:
        cursor = raw_conn.cursor()
        cursor.execute(POLICIES_SQL)
        raw_conn.commit()
        cursor.close()
        print("✓ All policies and permissions executed successfully.")
    finally:
        raw_conn.close()

    # Query active policies
    with engine.connect() as conn:
        policies = conn.execute(text("""
            SELECT tablename, policyname, roles, cmd 
            FROM pg_policies 
            WHERE schemaname = 'public' 
            ORDER BY tablename, policyname;
        """)).fetchall()

        print(f"\nActive pg_policies count: {len(policies)}")
        for p in policies:
            print(f"  - {p[0]:<32} | {p[1]:<45} | roles={p[2]} | cmd={p[3]}")
            
    print("=" * 70)

if __name__ == "__main__":
    apply_policies()
