"""
rotate_admin_credentials.py
===========================
Rotates default admin credentials in Supabase PostgreSQL database.
- Eliminates hardcoded 'admin_password'.
- Updates admin@recruit.ai password to a high-entropy cryptographically secure password.
- Updates backend/.env with the new ADMIN_PASSWORD and high-entropy SECRET_API_KEY.
- Verifies authentication with old vs new credentials.
"""
import sys
import os
import secrets
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv, set_key
env_path = backend_dir / '.env'
load_dotenv(env_path)

from core.database import SessionLocal
from core.auth import AuthUtils
from models.all_models import User

def rotate_credentials(custom_password=None):
    print("=" * 70)
    print("ROTATING TALENTAI ADMIN CREDENTIALS & API KEYS")
    print("=" * 70)

    # 1. Determine new secure password
    new_password = custom_password or os.getenv("ADMIN_PASSWORD")
    if not new_password or new_password == "admin_password":
        # Generate cryptographically secure 24-char password
        random_suffix = secrets.token_urlsafe(18)
        new_password = f"TalentAI_Secured_{random_suffix}"

    # Generate high-entropy SECRET_API_KEY if default or missing
    new_api_key = os.getenv("SECRET_API_KEY")
    if not new_api_key or new_api_key == "dev-secret-api-key":
        new_api_key = f"tai_{secrets.token_hex(24)}"

    # 2. Hash new password
    new_hash = AuthUtils.get_password_hash(new_password)

    # 3. Update in Supabase PostgreSQL
    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.email == "admin@recruit.ai").first()
        if not admin_user:
            print("Admin user not found in DB! Creating new admin user...")
            admin_user = User(
                email="admin@recruit.ai",
                hashed_password=new_hash,
                role="ADMIN",
                is_active=True,
                organization_id="org_talentai_default"
            )
            db.add(admin_user)
        else:
            print(f"Found admin user (ID={admin_user.id}, Email={admin_user.email}). Updating hashed_password...")
            admin_user.hashed_password = new_hash
            admin_user.is_active = True

        db.commit()
        db.refresh(admin_user)
        print("[+] Successfully updated admin password hash in Supabase database!")
    except Exception as e:
        db.rollback()
        print(f"[-] Failed to update database: {e}")
        db.close()
        sys.exit(1)
    finally:
        db.close()

    # 4. Update backend/.env file
    try:
        if env_path.exists():
            set_key(str(env_path), "ADMIN_PASSWORD", new_password)
            set_key(str(env_path), "SECRET_API_KEY", new_api_key)
            print("[+] Updated backend/.env with ADMIN_PASSWORD and SECRET_API_KEY.")
        else:
            with open(env_path, "a") as f:
                f.write(f"\nADMIN_PASSWORD={new_password}\nSECRET_API_KEY={new_api_key}\n")
            print("[+] Created entries in backend/.env.")
    except Exception as e:
        print(f"Warning: Could not write to .env: {e}")

    # 5. Verify password verification logic
    db = SessionLocal()
    admin_user = db.query(User).filter(User.email == "admin@recruit.ai").first()
    old_valid = AuthUtils.verify_password("admin_password", admin_user.hashed_password)
    new_valid = AuthUtils.verify_password(new_password, admin_user.hashed_password)
    db.close()

    print("\n--- Credential Verification ---")
    print(f"Old password ('admin_password') accepted?: {old_valid} (Must be False)")
    print(f"New password accepted?:                  {new_valid} (Must be True)")
    print(f"Admin Email:                             admin@recruit.ai")
    print(f"New Secure Password:                     {new_password}")
    print(f"New SECRET_API_KEY:                      {new_api_key}")
    print("=" * 70)

    assert not old_valid, "CRITICAL ERROR: Old default password still validates!"
    assert new_valid, "CRITICAL ERROR: New password failed to validate!"
    print("SUCCESS: Default admin credentials successfully purged and rotated.")
    return new_password, new_api_key

if __name__ == "__main__":
    rotate_credentials()
