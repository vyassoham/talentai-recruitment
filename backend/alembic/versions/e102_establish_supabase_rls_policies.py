"""establish_supabase_rls_policies

Revision ID: e102_supabase_rls_policies
Revises: e101_multitenant_orgs
Create Date: 2026-10-29 00:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e102_supabase_rls_policies'
down_revision: Union[str, Sequence[str], None] = 'e101_multitenant_orgs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Helper function for tenant resolution from JWT or session
    op.execute("""
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
    """)

    # 2. Sequence permissions for authenticated users
    op.execute("""
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon;
        REVOKE INSERT, UPDATE, DELETE, TRUNCATE, TRIGGER, REFERENCES ON ALL TABLES IN SCHEMA public FROM anon;
    """)

    # 3. Enable RLS on core tables
    tables = [
        'candidates', 'job_requirements', 'recruiter_feedback', 'organizations',
        'users', 'candidate_documents', 'candidate_demographics', 'candidate_skills',
        'candidate_section_embeddings', 'employment', 'evaluation_evidence',
        'ingestion_jobs', 'background_jobs', 'ai_registry', 'ontology'
    ]
    for table in tables:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;")

    # 4. Clean up any preexisting policies to prevent duplicate policy errors
    policies_to_drop = [
        ('candidates', 'candidates_tenant_isolation'),
        ('job_requirements', 'job_requirements_tenant_isolation'),
        ('recruiter_feedback', 'recruiter_feedback_tenant_isolation'),
        ('organizations', 'organizations_tenant_isolation'),
        ('users', 'users_tenant_isolation'),
        ('candidate_documents', 'candidate_documents_tenant_isolation'),
        ('candidate_demographics', 'candidate_demographics_tenant_isolation'),
        ('candidate_skills', 'candidate_skills_tenant_isolation'),
        ('candidate_section_embeddings', 'candidate_section_embeddings_tenant_isolation'),
        ('employment', 'employment_tenant_isolation'),
        ('evaluation_evidence', 'evaluation_evidence_tenant_isolation'),
        ('ingestion_jobs', 'ingestion_jobs_tenant_isolation'),
        ('ontology', 'ontology_read_policy'),
    ]
    for tbl, pol in policies_to_drop:
        op.execute(f"DROP POLICY IF EXISTS {pol} ON public.{tbl};")

    # 5. Create production RLS policies
    op.execute("""
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
    """)


def downgrade() -> None:
    policies_to_drop = [
        ('candidates', 'candidates_tenant_isolation'),
        ('job_requirements', 'job_requirements_tenant_isolation'),
        ('recruiter_feedback', 'recruiter_feedback_tenant_isolation'),
        ('organizations', 'organizations_tenant_isolation'),
        ('users', 'users_tenant_isolation'),
        ('candidate_documents', 'candidate_documents_tenant_isolation'),
        ('candidate_demographics', 'candidate_demographics_tenant_isolation'),
        ('candidate_skills', 'candidate_skills_tenant_isolation'),
        ('candidate_section_embeddings', 'candidate_section_embeddings_tenant_isolation'),
        ('employment', 'employment_tenant_isolation'),
        ('evaluation_evidence', 'evaluation_evidence_tenant_isolation'),
        ('ingestion_jobs', 'ingestion_jobs_tenant_isolation'),
        ('ontology', 'ontology_read_policy'),
    ]
    for tbl, pol in policies_to_drop:
        op.execute(f"DROP POLICY IF EXISTS {pol} ON public.{tbl};")

    op.execute("DROP FUNCTION IF EXISTS public.current_org_id();")
