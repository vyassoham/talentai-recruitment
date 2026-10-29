"""
repair_candidate_profiles_phase3.py
===================================
Phase 3 Candidate Name Repair Engine for TalentAI Enterprise Platform.

Targets:
1. Exact 'Candidate Profile' records
2. Job titles accidentally parsed as names ('Java Developer', 'Devops Engineer', 'Principal Consultant')
3. Location/Contact headers ('Location Pune Email', 'Bangalore India', 'Email Mobile')
4. Spaced/split letters ('R A M E S H  T H U M A T I')
5. Prefixed titles ('Mr. Mayur Satish Avhad', 'Full Name: Nandakumar B.M', 'Nikhil Garg Technical Manager')

Guarantees:
- 100% Free & Local: Uses pure Python heuristics, regex, and NLP token validation (no paid LLM calls).
- Zero Hallucination: Verifies extracted candidate names against CV body and/or candidate email.
- Complete Backup: Logs every update to candidate_name_backup_20261028.
- Transactional: Commits atomically in SQLAlchemy.
"""
import os
import sys
import re
import json
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Ensure immediate unbuffered output
sys.stdout.reconfigure(line_buffering=True)

backend_dir = Path(r"D:\recruitment_platform\backend")
load_dotenv(backend_dir / '.env')
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from core.database import SessionLocal
from models.all_models import Candidate

STOP_WORDS = {
    # CV Sections & Document tokens
    'resume', 'curriculum', 'vitae', 'cv', 'profile', 'summary', 'objective', 'career',
    'experience', 'education', 'skills', 'technical', 'overview', 'projects', 'contact',
    'email', 'phone', 'address', 'page', 'details', 'personal', 'declaration', 'name',
    'full', 'date', 'birth', 'gender', 'nationality', 'languages', 'hobbies', 'certifications',
    'strengths', 'competencies', 'highlights', 'professional', 'experienced', 'seeking',
    'looking', 'motivated', 'enthusiastic', 'work', 'history', 'employment', 'cell', 'website',
    'portfolio', 'linkedin', 'github', 'ats', 'compatible', 'mobile', 'tel', 'powered', 'by',
    'enhancv', 'novoresume', 'overleaf', 'canva', 'com', 'www', 'http', 'https', 'id', 'no',
    'having', 'with', 'years', 'year', 'exp', 'expert', 'professoinal', 'total', 'relevant',
    'in', 'of', 'and', 'the', 'for', 'to', 'from', 'at', 'as', 'on', 'an', 'a', 'is', 'it', 'or',
    'poised', 'focused', 'app', 'results', 'oriented', 'about', 'my', 'stack', 'senior', 'junior',
    'lead', 'gajanand', 'iiith', 'ugee', 'ncr', 'digital', 'strategist', 'solutions', 'it', 'tech',
    'technologies', 'college', 'university', 'school', 'degree', 'btech', 'mtech', 'bca', 'mca',
    'be', 'me', 'bsc', 'msc', 'passionate', 'skilled', 'dedicated', 'driven', 'learning',

    # Job Titles & Roles
    'developer', 'engineer', 'manager', 'consultant', 'architect', 'lead', 'analyst',
    'associate', 'intern', 'fresher', 'specialist', 'administrator', 'trainee', 'director',
    'officer', 'executive', 'programmer', 'tester', 'qa', 'sdet', 'lead', 'head', 'vp',
    'freelancer', 'contractor', 'student', 'candidate', 'member', 'coder', 'writer', 'scrum', 'master',
    'listing', 'compliance', 'corporate', 'department', 'bse', 'nse', 'sebi',

    # Locations
    'bengaluru', 'bangalore', 'india', 'pune', 'hyderabad', 'mumbai', 'delhi', 'chennai',
    'noida', 'gurgaon', 'gurugram', 'karnataka', 'maharashtra', 'tamil', 'nadu', 'telangana',
    'kolkata', 'ahmedabad', 'gujarat', 'kerala', 'kochi', 'jaipur', 'chandigarh', 'ka', 'tn',
    'ap', 'ts', 'mh', 'dl', 'location', 'city', 'state', 'country', 'pin', 'remote',
    'solapur', 'hadapsar', 'navi', 'vashi', 'agastheespuram', 'haryana',

    # Tech skills & stacks
    'salesforce', 'aws', 'etl', 'java', 'python', 'react', 'angular', 'node', 'nodejs',
    'dotnet', 'sql', 'devops', 'cloud', 'fullstack', 'frontend', 'backend', 'azure', 'gcp',
    'spark', 'hadoop', 'c', 'cpp', 'csharp', 'php', 'ruby', 'golang', 'docker', 'kubernetes',
    'linux', 'tableau', 'powerbi', 'power', 'bi', 'biw', 'sap', 'oracle', 'jira', 'agile',
    'selenium', 'manual', 'automation', 'test', 'testing', 'embedded', 'cyber',
    'security', 'devsecops', 'network', 'support', 'database', 'dba', 'data', 'science',
    'ai', 'ml', 'nlp', 'deep', 'pvt', 'ltd', 'inc', 'corp', 'company', 'genpact', 'kaar',
    'tcs', 'infosys', 'wipro', 'cognizant', 'capgemini', 'vichara'
}

def clean_token(token: str) -> str:
    tok = token.strip()
    tok = re.sub(r'^[^\w]+|[^\w\.]+$', '', tok)
    return tok

def is_valid_name_token(token: str) -> bool:
    tok = clean_token(token)
    if not tok:
        return False
    lower = tok.lower().rstrip('.')
    if lower in STOP_WORDS:
        return False
    if re.match(r'^[A-Za-z]{2,25}$', tok):
        return True
    if re.match(r'^[A-Za-z]\.?$', tok):
        return True
    return False

def normalize_spaced_letters(line: str) -> str:
    tokens = line.split()
    words = []
    current_word = []
    for t in tokens:
        if len(t) == 1 and t.isalpha():
            current_word.append(t)
        else:
            if current_word:
                if len(current_word) >= 2:
                    words.append(''.join(current_word))
                else:
                    words.extend(current_word)
                current_word = []
            words.append(t)
    if current_word:
        if len(current_word) >= 2:
            words.append(''.join(current_word))
        else:
            words.extend(current_word)
    return ' '.join(words)

def clean_and_format_name(raw_name: str) -> str:
    s = raw_name.strip()
    
    # Strip leading LinkedIn badges or titles
    s = re.sub(r'^(?:in|linkedin)\s+', '', s, flags=re.IGNORECASE)
    s = re.sub(r'^(?:mr|ms|mrs|dr|prof)\.?\s+', '', s, flags=re.IGNORECASE)
    s = re.sub(r'^(?:full\s+name|candidate\s+name|name)\s*[\:\-\–]?\s*', '', s, flags=re.IGNORECASE)
    s = re.sub(r'^(?:curriculum\s+vitae|resume|cv)\s*[\:\-\–]?\s*', '', s, flags=re.IGNORECASE)

    # Strip trailing email/contact prefixes like 'E. Mail', 'Email:', etc.
    s = re.sub(r'\s+[eE][\.\s-]?\s*(?:mail|email|mailto).*$', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s+(?:email|mail|phone|mobile|cell|contact|id|no)[\s\:\-\–].*$', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s+[0-9a-fA-F]{6,}\b.*$', '', s)
    s = re.sub(r'\s+(?:technical\s+manager|project\s+manager|team\s+lead|software\s+engineer|developer|consultant|architect|lead|writer|scrum\s+master).*$', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s+[\-\–\|].*$', '', s)

    tokens = [clean_token(t) for t in s.split() if t.strip()]
    tokens = [t for t in tokens if is_valid_name_token(t)]
    if not tokens:
        return ""

    formatted = []
    for t in tokens:
        if len(t) == 1 or (len(t) == 2 and t.endswith('.')):
            formatted.append(t[0].upper() + '.')
        else:
            formatted.append(t.capitalize())

    return ' '.join(formatted)

def extract_name_from_cv(raw_text: str, email: str, current_name: str) -> tuple[str, str, str]:
    if not raw_text:
        return None, "NONE", "NO_TEXT"

    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    header_lines = lines[:15]

    email_parts = []
    if email and email.lower() != 'none' and '@' in email:
        email_user = email.split('@')[0].lower()
        cleaned_user = re.sub(r'[\d\._\-]+', ' ', email_user)
        email_parts = [p for p in cleaned_user.split() if len(p) >= 3 and p not in STOP_WORDS]

    # Strategy A: Check current_name with trailing title to strip
    if current_name and current_name != 'Candidate Profile':
        cleaned_current = clean_and_format_name(current_name)
        tokens = cleaned_current.split()
        if 2 <= len(tokens) <= 4:
            if not any(t.lower().rstrip('.') in STOP_WORDS for t in tokens):
                # Must be confirmed by email
                if email_parts and any(p in [t.lower().rstrip('.') for t in tokens if len(t) > 2] for p in email_parts):
                    return cleaned_current, "HIGH", "STRIPPED_TITLE_CONFIRMED_BY_EMAIL"

    # Strategy B: CV Header Lines
    for idx, line in enumerate(header_lines[:12]):
        line = normalize_spaced_letters(line)
        line_clean = re.sub(r'https?://\S+', '', line)
        line_clean = re.sub(r'[\w\.-]+@[\w\.-]+', '', line_clean)
        line_clean = re.sub(r'(\+91|tel|phone|mob|contact|email|cell|location)[\s\:\+\-\d]+', '', line_clean, flags=re.IGNORECASE)
        line_clean = re.sub(r'[\(\)\[\]\{\}\|\/\:\.\,\_\-]', ' ', line_clean)

        candidate_name = clean_and_format_name(line_clean)
        tokens = candidate_name.split()

        if 2 <= len(tokens) <= 4:
            if any(t.lower().rstrip('.') in STOP_WORDS for t in tokens):
                continue

            # Confirmed by email username
            if email_parts:
                token_lowers = [t.lower().rstrip('.') for t in tokens if len(t) > 2]
                if any(p in token_lowers or any(tok in p for tok in token_lowers) for p in email_parts):
                    return candidate_name, "HIGH", f"CV_LINE_{idx+1}_CONFIRMED_BY_EMAIL"

    # Strategy C: Multi-line consecutive name tokens
    consecutive_tokens = []
    for idx in range(min(8, len(header_lines))):
        line = header_lines[idx].strip()
        line = re.sub(r'https?://\S+|[\w\.-]+@[\w\.-]+', '', line)
        words = line.split()
        if len(words) == 1:
            w = clean_token(words[0])
            if is_valid_name_token(w) and len(w) >= 2:
                consecutive_tokens.append(w)
                if len(consecutive_tokens) >= 2:
                    potential_name = clean_and_format_name(' '.join(consecutive_tokens))
                    tokens = potential_name.split()
                    if 2 <= len(tokens) <= 4:
                        if email_parts and any(p in [t.lower().rstrip('.') for t in tokens] for p in email_parts):
                            return potential_name, "HIGH", "MULTI_LINE_SPLIT_CONFIRMED_BY_EMAIL"
            else:
                consecutive_tokens = []
        else:
            consecutive_tokens = []

    # Strategy D: LinkedIn profile URL slug in CV text
    li_match = re.search(r'linkedin\.com/in/([a-zA-Z0-9\-_]+)', raw_text[:2000], re.IGNORECASE)
    if li_match:
        slug = li_match.group(1).lower()
        slug_clean = re.sub(r'[0-9a-fA-F]{6,}', '', slug) # strip hex hashes
        slug_parts = [clean_token(p).capitalize() for p in re.split(r'[\-_]+', slug_clean) if len(p) >= 2 and not p.isdigit() and p.lower() not in STOP_WORDS]
        if 2 <= len(slug_parts) <= 3:
            li_name = ' '.join(slug_parts)
            if all(p.lower() in raw_text[:1500].lower() for p in slug_parts):
                return li_name, "HIGH", "LINKEDIN_SLUG_VERIFIED_IN_CV"

    return None, "NONE", "NO_RELIABLE_NAME_FOUND"

def run_phase3_repair(apply_changes: bool = False):
    print("=" * 75)
    print(f"TALENTAI CANDIDATE NAME REPAIR - PHASE 3 ({'APPLY MODE' if apply_changes else 'DRY RUN ONLY'})")
    print("=" * 75)

    db = SessionLocal()

    query_sql = """
        SELECT c.id, c.name, c.email, cd.raw_extracted_text, cd.original_filename
        FROM candidates c
        LEFT JOIN candidate_documents cd ON c.id = cd.candidate_id
        WHERE c.name = 'Candidate Profile'
           OR c.name ILIKE '%developer%'
           OR c.name ILIKE '%engineer%'
           OR c.name ILIKE '%consultant%'
           OR c.name ILIKE '%manager%'
           OR c.name ILIKE '%location %'
           OR c.name ILIKE '%bangalore%'
           OR c.name ILIKE '%pune%'
           OR c.name ILIKE '%hyderabad%'
           OR c.name ILIKE '%mumbai%'
           OR c.name ILIKE '%delhi%'
           OR c.name ILIKE '%chennai%'
           OR c.name ILIKE '%email %'
           OR c.name ILIKE '%powered by%'
           OR c.name ILIKE '%curriculum%'
           OR c.name ILIKE '%resume%'
           OR c.name ILIKE '%architect%'
           OR c.name ILIKE '%specialist%'
           OR c.name ILIKE '%analyst%'
           OR c.name ILIKE '%administrator%'
           OR c.name ILIKE '%programmer%'
           OR c.name ILIKE '%tester%'
           OR c.name ILIKE '%fresher%'
           OR c.name ILIKE '%experience%'
           OR c.name ILIKE '%summary%'
           OR c.name ILIKE '%objective%'
           OR c.name ILIKE '%overview%'
           OR c.name ILIKE '%page %'
           OR c.name = 'Synth'
           OR c.name IS NULL
           OR trim(c.name) = '';
    """
    rows = db.execute(text(query_sql)).fetchall()
    print(f"Fetched {len(rows)} target candidate records with documents in single batch query.")

    high_repairs = []
    unresolved = []

    for cid, orig_name, email, raw_text, filename in rows:
        repaired_name, conf, rule = extract_name_from_cv(raw_text or "", email or "", orig_name or "")

        item = {
            "candidate_id": cid,
            "original_name": orig_name,
            "repaired_name": repaired_name,
            "confidence": conf,
            "rule": rule,
            "email": email,
            "filename": filename or ""
        }

        if conf == "HIGH" and repaired_name and repaired_name != orig_name:
            high_repairs.append(item)
        else:
            unresolved.append(item)

    print(f"\n[+] High-Confidence Verified Repairs: {len(high_repairs)}")
    print(f"[-] Unresolved / Preserved Untouched:  {len(unresolved)}")

    print("\n--- SAMPLE HIGH-CONFIDENCE REPAIRS (First 30) ---")
    for r in high_repairs[:30]:
        print(f"ID={r['candidate_id']:<5} | '{r['original_name']}' -> '{r['repaired_name']}' | Rule: {r['rule']}")

    audit_path = backend_dir / "candidate_name_repair_phase3_audit.json"
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "mode": "APPLY" if apply_changes else "DRY_RUN",
            "total_candidates_analyzed": len(rows),
            "high_repairs_count": len(high_repairs),
            "unresolved_count": len(unresolved),
            "repairs": high_repairs
        }, f, indent=2)
    print(f"\n[+] Audit report saved to {audit_path}")

    if apply_changes and high_repairs:
        print("\n" + "=" * 75)
        print(f"COMMITTING {len(high_repairs)} REPAIRS TO SUPABASE DATABASE...")
        print("=" * 75)

        for r in high_repairs:
            db.execute(text("""
                INSERT INTO candidate_name_backup_20261028 
                (candidate_id, original_name, repaired_name, confidence, evidence_source, backed_up_at, is_active_repair)
                VALUES (:cid, :orig, :repaired, :conf, :ev, :ts, true)
            """), {
                "cid": r["candidate_id"],
                "orig": r["original_name"],
                "repaired": r["repaired_name"],
                "conf": r["confidence"],
                "ev": r["rule"],
                "ts": datetime.now()
            })

            cand = db.get(Candidate, r["candidate_id"])
            if cand:
                cand.name = r["repaired_name"]

        db.commit()
        print(f"[SUCCESS] {len(high_repairs)} candidate names successfully repaired and backed up in Supabase!")
    else:
        print("\n(Run with --apply to commit these verified repairs to Supabase PostgreSQL)")

    db.close()
    return high_repairs

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Commit repairs to Supabase")
    args = parser.parse_args()
    run_phase3_repair(apply_changes=args.apply)
