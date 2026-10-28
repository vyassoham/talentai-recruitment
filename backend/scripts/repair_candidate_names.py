"""
TalentAI Candidate Name Repair Utility
--------------------------------------
Fixes candidates with corrupt names (e.g. 'Maintaining It Infrastructure', 'Candidate Profile', 'Bengaluru India')
by inferring genuine human names from verified email usernames and resume body lines.

Usage:
    python backend/scripts/repair_candidate_names.py --dry-run
    python backend/scripts/repair_candidate_names.py --apply
"""

import os
import sys
import re
import argparse
from dotenv import load_dotenv

load_dotenv('D:/recruitment_platform/backend/.env')
sys.path.insert(0, 'D:/recruitment_platform/backend')

from core.database import SessionLocal
from models.all_models import Candidate, CandidateDocument

BAD_NAME_PATTERNS = [
    'India', 'Bangalore', 'Bengaluru', 'Resume', 'Profile', 'Maintaining',
    'Documentation', 'Keyimpact', 'Curriculum', 'Karnataka', 'Summary',
    'Experience', 'Operational', 'Benefits', 'Sourcebae', 'Education',
    'Career', 'Objective', 'Professional', 'Skills', 'Technical', 'Overview'
]

def is_bad_name(name: str) -> bool:
    if not name or len(name.strip()) < 3:
        return True
    lower = name.lower()
    for bad in BAD_NAME_PATTERNS:
        if bad.lower() in lower:
            return True
    words = name.split()
    if len(words) > 5:
        return True
    return False

def clean_email_username(email: str) -> str:
    if not email or '@' not in email:
        return ""
    username = email.split('@')[0].strip()
    # Remove unwanted trailing/leading words
    username = re.sub(r'(?:frontend|backend|developer|engineer|java|python|pes\d*|bits\d*)$', '', username, flags=re.IGNORECASE)
    # Replace numbers, underscores, hyphens, dots with spaces
    cleaned = re.sub(r'[\d_\.\-]+', ' ', username).strip()
    parts = [p.capitalize() for p in cleaned.split() if len(p) >= 2]
    
    # Filter out generic terms
    filtered = [p for p in parts if p.lower() not in ['resume', 'profile', 'info', 'mail', 'contact', 'user', 'candidate', 'inbox']]
    if filtered:
        candidate_name = ' '.join(filtered)
        if 3 <= len(candidate_name) <= 35:
            return candidate_name
    return ""

def infer_name_from_cv(text: str) -> str:
    if not text:
        return ""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for l in lines[:6]:
        # Strip bullets or extra symbols
        clean_l = re.sub(r'^[•\-\*\d\.\s]+', '', l).strip()
        words = clean_l.split()
        if 2 <= len(words) <= 4 and all(w.isalpha() for w in words):
            if not is_bad_name(clean_l):
                return clean_l.title()
    return ""

def main():
    parser = argparse.ArgumentParser(description="Repair corrupt candidate names in TalentAI Supabase DB.")
    parser.add_argument("--apply", action="store_true", help="Apply fixes directly to the database.")
    args = parser.parse_args()

    db = SessionLocal()
    candidates = db.query(Candidate).all()
    
    repaired = 0
    skipped = 0
    samples = []

    print(f"Scanning {len(candidates)} candidates for corrupt names...")

    for c in candidates:
        if is_bad_name(c.name):
            # 1. Try email extraction
            new_name = clean_email_username(c.email)
            
            # 2. If no valid name from email, try CV lines
            if not new_name and c.documents:
                doc = c.documents[0]
                raw_text = doc.raw_extracted_text or doc.normalized_text or ""
                new_name = infer_name_from_cv(raw_text)

            if new_name:
                if len(samples) < 15:
                    samples.append((c.id, c.name, new_name, c.email))
                if args.apply:
                    c.name = new_name
                repaired += 1
            else:
                skipped += 1

    print("\n" + "=" * 60)
    print(f"REPAIR SUMMARY ({'APPLIED TO DB' if args.apply else 'DRY RUN ONLY'})")
    print("=" * 60)
    print(f"Total Corrupt Names Found:    {repaired + skipped}")
    print(f"Successfully Recovered Names: {repaired}")
    print(f"Unrecoverable Names:          {skipped}")
    print("=" * 60)

    print("\nSAMPLE RECOVERED NAMES:")
    for cid, old_n, new_n, em in samples:
        print(f"  [ID {cid}]  \"{old_n}\"  -->  \"{new_n}\"  (Email: {em})")

    if args.apply:
        db.commit()
        print("\n[SUCCESS] Changes committed to Supabase production database.")
    else:
        print("\n[NOTE] Dry run complete. No database changes were made. Pass --apply to persist changes.")

    db.close()

if __name__ == '__main__':
    main()
