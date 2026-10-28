"""
TalentAI Autonomous Background Vector Embedding Daemon
======================================================
Author: Principal AI Infrastructure & DevOps Engineer
Mission: Automatically populates 1536-dimensional Gemini pgvector embeddings across
         all pending candidates, self-throttling and sleeping across daily quota resets
         until 100% of candidate records in Supabase are vector-embedded.

Features:
- Completely autonomous: Detects quota exhaustion, sleeps until exact reset time, resumes automatically.
- Checkpointed & Idempotent: Every success updates candidate_embedding in DB and progress on disk.
- Zero Loss: Unaffected by container restarts.
- Auto-terminates when 100% candidate embedding coverage is achieved.
"""
import os
import sys
import re
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv(r'D:\recruitment_platform\backend\.env')
sys.path.insert(0, r'D:\recruitment_platform\backend')

from core.database import SessionLocal
from models.all_models import Candidate
from scripts.generate_candidate_embeddings import CandidateEmbeddingPopulator

def parse_retry_seconds(error_msg: str) -> int:
    """Extracts seconds to wait from Gemini's 'Please retry in XhYmZs' error message."""
    if not error_msg:
        return 3600 * 6  # fallback: 6 hours
    match = re.search(r'retry in\s+(?:(\d+)h)?(?:(\d+)m)?(?:([\d\.]+)s)?', error_msg, re.IGNORECASE)
    if match:
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = float(match.group(3) or 0)
        return int(hours * 3600 + minutes * 60 + seconds)
    return 3600 * 6

def get_pending_count() -> tuple[int, int]:
    db = SessionLocal()
    total = db.query(Candidate).count()
    pending = db.query(Candidate).filter(Candidate.embedding.is_(None)).count()
    db.close()
    return total, pending

def run_daemon():
    print("=" * 70)
    print("TALENTAI AUTONOMOUS BACKGROUND EMBEDDING DAEMON")
    print("=" * 70)

    progress_file = r"D:\recruitment_platform\backend\storage\embedding_progress.json"

    iteration = 1
    while True:
        total, pending = get_pending_count()
        embedded = total - pending
        pct = (embedded / total) * 100 if total > 0 else 0.0

        print(f"\n[DAEMON ITERATION {iteration}] Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Candidates:     {total}")
        print(f"Embedded Candidates:  {embedded} ({pct:.1f}%)")
        print(f"Pending Embeddings:   {pending}")
        print("-" * 70)

        if pending == 0:
            print("\n" + "=" * 70)
            print("[SUCCESS] 100% OF CANDIDATES HAVE VALID VECTOR EMBEDDINGS!")
            print("=" * 70)
            populator = CandidateEmbeddingPopulator(progress_file)
            populator.validate_vector_search()
            populator.close()
            break

        populator = CandidateEmbeddingPopulator(progress_file)
        result = populator.populate(limit=500, batch_size=5, delay_sec=0.5)
        populator.close()

        if result.get("quota_exceeded"):
            err_str = result.get("error", "")
            sleep_sec = parse_retry_seconds(err_str)
            # Add 90 seconds safety buffer
            sleep_sec += 90

            wake_time = datetime.now() + timedelta(seconds=sleep_sec)
            hours = sleep_sec // 3600
            minutes = (sleep_sec % 3600) // 60
            
            print("\n" + "!" * 70)
            print(f"[QUOTA REACHED] Daily Free Tier Embedding Limit Exceeded.")
            print(f"Sleeping for {hours}h {minutes}m ({sleep_sec}s).")
            print(f"Scheduled Resume Time: {wake_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print("!" * 70)
            print("Waiting for quota reset...")

            # Sleep in intervals of 60 seconds to allow clean termination if stopped
            slept = 0
            while slept < sleep_sec:
                chunk = min(60, sleep_sec - slept)
                time.sleep(chunk)
                slept += chunk

            print(f"\n[WAKING UP] Resuming embedding generation at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
        else:
            # If no quota exceeded but limit batch finished, pause briefly and loop
            time.sleep(2.0)

        iteration += 1

if __name__ == '__main__':
    run_daemon()
