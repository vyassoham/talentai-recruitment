"""
test_database_rls.py
====================
Automated verification tests for Supabase Row-Level Security (RLS) policies.
Ensures database-engine-level multi-tenant defense-in-depth:
- postgres/service_role retains BypassRLS for backend operations.
- anon role is shielded from candidate and job data.
- authenticated users are strictly isolated by their JWT org_id claim.
- cross-tenant inserts are rejected by RLS WITH CHECK constraint.
"""
import pytest
from sqlalchemy import text
from core.database import engine


@pytest.fixture(scope="module")
def db_connection():
    raw_conn = engine.raw_connection()
    yield raw_conn
    raw_conn.close()


def test_postgres_bypassrls_status(db_connection):
    """Ensure the backend connection role bypasses RLS for Celery/FastAPI."""
    cursor = db_connection.cursor()
    cursor.execute("""
        SELECT rolname, rolbypassrls 
        FROM pg_roles 
        WHERE rolname = CURRENT_USER;
    """)
    role_info = cursor.fetchone()
    cursor.close()
    assert role_info is not None
    assert role_info[1] is True, f"Role {role_info[0]} must have BypassRLS = True"


def test_rls_enabled_on_core_tables(db_connection):
    """Ensure all core multi-tenant tables have row-level security enabled."""
    cursor = db_connection.cursor()
    cursor.execute("""
        SELECT tablename, rowsecurity 
        FROM pg_tables 
        WHERE schemaname = 'public' 
          AND tablename IN (
            'candidates', 'job_requirements', 'organizations', 
            'recruiter_feedback', 'candidate_documents', 'users',
            'candidate_demographics', 'candidate_skills', 
            'candidate_section_embeddings', 'employment', 
            'evaluation_evidence', 'ingestion_jobs'
          );
    """)
    rows = cursor.fetchall()
    cursor.close()
    assert len(rows) >= 12
    for tbl, rls in rows:
        assert rls is True, f"Table {tbl} must have rowsecurity = True"


def test_pg_policies_count(db_connection):
    """Ensure active security policies exist in pg_policies."""
    cursor = db_connection.cursor()
    cursor.execute("""
        SELECT tablename, policyname, roles, cmd 
        FROM pg_policies 
        WHERE schemaname = 'public';
    """)
    policies = cursor.fetchall()
    cursor.close()
    assert len(policies) >= 13, f"Expected at least 13 policies, found {len(policies)}"


def test_anon_role_shielded_from_candidates(db_connection):
    """Ensure anon role receives 0 candidates via RLS."""
    cursor = db_connection.cursor()
    cursor.execute("SET ROLE anon;")
    try:
        cursor.execute("SELECT count(*) FROM candidates;")
        count = cursor.fetchone()[0]
        assert count == 0, f"Anon role must see 0 candidates, got {count}"
    finally:
        cursor.execute("RESET ROLE;")
        cursor.close()


def test_anon_role_shielded_from_jobs(db_connection):
    """Ensure anon role receives 0 job requirements via RLS."""
    cursor = db_connection.cursor()
    cursor.execute("SET ROLE anon;")
    try:
        cursor.execute("SELECT count(*) FROM job_requirements;")
        count = cursor.fetchone()[0]
        assert count == 0, f"Anon role must see 0 jobs, got {count}"
    finally:
        cursor.execute("RESET ROLE;")
        cursor.close()


def test_anon_role_can_read_ontology(db_connection):
    """Ensure public taxonomy (ontology) is readable by anon."""
    cursor = db_connection.cursor()
    cursor.execute("SET ROLE anon;")
    try:
        cursor.execute("SELECT count(*) FROM ontology;")
        count = cursor.fetchone()[0]
        assert count >= 0
    finally:
        cursor.execute("RESET ROLE;")
        cursor.close()


def test_anon_role_insert_denied(db_connection):
    """Ensure anon role cannot insert into candidates."""
    cursor = db_connection.cursor()
    cursor.execute("SET ROLE anon;")
    blocked = False
    try:
        cursor.execute("INSERT INTO candidates (name, email) VALUES ('Anon', 'anon@test.com');")
    except Exception:
        blocked = True
    finally:
        db_connection.rollback()
        c2 = db_connection.cursor()
        c2.execute("RESET ROLE;")
        c2.close()
    assert blocked, "Anon INSERT must be blocked"


def test_authenticated_tenant_isolation_reads(db_connection):
    """Ensure authenticated role only sees data belonging to its JWT org_id."""
    cursor = db_connection.cursor()
    cursor.execute("SET ROLE authenticated;")
    try:
        # 1. With org_talentai_default claim
        cursor.execute("SET LOCAL \"request.jwt.claims\" = '{\"org_id\": \"org_talentai_default\", \"role\": \"authenticated\"}';")
        cursor.execute("SELECT count(*) FROM candidates;")
        default_count = cursor.fetchone()[0]
        assert default_count > 0, "Default tenant should see its candidate pool"

        # 2. With competitor claim
        cursor.execute("SET LOCAL \"request.jwt.claims\" = '{\"org_id\": \"org_competitor_isolated\", \"role\": \"authenticated\"}';")
        cursor.execute("SELECT count(*) FROM candidates;")
        comp_count = cursor.fetchone()[0]
        assert comp_count == 0, "Competitor tenant must see 0 candidates from default tenant"
    finally:
        cursor.execute("RESET ROLE;")
        cursor.close()


def test_authenticated_cross_tenant_insert_blocked(db_connection):
    """Ensure authenticated tenant cannot insert records with another tenant's org_id."""
    cursor = db_connection.cursor()
    cursor.execute("SET ROLE authenticated;")
    cursor.execute("SET LOCAL \"request.jwt.claims\" = '{\"org_id\": \"org_competitor_isolated\", \"role\": \"authenticated\"}';")
    blocked = False
    try:
        cursor.execute("""
            INSERT INTO candidates (name, email, organization_id)
            VALUES ('Malicious Candidate', 'mal@test.com', 'org_talentai_default');
        """)
    except Exception:
        blocked = True
    finally:
        db_connection.rollback()
        c2 = db_connection.cursor()
        c2.execute("RESET ROLE;")
        c2.close()
    assert blocked, "Cross-tenant INSERT must violate RLS WITH CHECK policy"
