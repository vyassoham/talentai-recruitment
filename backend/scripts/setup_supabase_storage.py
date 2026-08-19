from sqlalchemy import create_engine, text
from core.config import settings

engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    # Ensure bucket exists and is public
    conn.execute(text("INSERT INTO storage.buckets (id, name, public) VALUES ('resumes', 'resumes', true) ON CONFLICT (id) DO UPDATE SET public = true;"))
    conn.commit()

    # Apply policy for full CRUD on resumes bucket
    conn.execute(text("""
        DROP POLICY IF EXISTS "Public Resumes Access" ON storage.objects;
        CREATE POLICY "Public Resumes Access" ON storage.objects FOR ALL USING (bucket_id = 'resumes') WITH CHECK (bucket_id = 'resumes');
    """))
    conn.commit()
    print("Storage bucket 'resumes' and RLS policy configured successfully!")
