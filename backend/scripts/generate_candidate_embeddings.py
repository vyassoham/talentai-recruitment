"""
TalentAI Enterprise Vector Embedding Ingestion & Validation Engine
==================================================================
Author: Principal AI Infrastructure & Database Reliability Engineer
Mission: Generate and persist 1536-dimensional Gemini vector embeddings in Supabase pgvector.

Guarantees:
1. Restartable & Idempotent: Resumes from last checkpoint saved in embedding_progress.json.
2. Rich Profile Synthesis: Encodes name, title, experience, full skills, and employment history.
3. Both Global Summary & Section Embeddings populated.
4. Rate Pacing & Exponential Backoff: Protects Gemini API quotas.
5. End-to-End pgvector Validation: Runs a live cosine distance query to verify semantic retrieval.
"""
import os
import sys
import json
import time
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv(r'D:\recruitment_platform\backend\.env')
sys.path.insert(0, r'D:\recruitment_platform\backend')

from sqlalchemy import text
from core.database import SessionLocal
from models.all_models import Candidate, CandidateSectionEmbedding
from services.ai.provider import get_ai_provider
from services.ai.embeddings import EmbeddingsService

class CandidateEmbeddingPopulator:
    def __init__(self, progress_file: str):
        self.progress_file = os.path.abspath(progress_file)
        self.db = SessionLocal()
        self.provider = get_ai_provider()
        self.progress = self._load_progress()

    def _load_progress(self) -> Dict[str, Any]:
        if os.path.isfile(self.progress_file):
            try:
                with open(self.progress_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "last_processed_candidate_id": 0,
            "total_embeddings_generated": 0,
            "failed_candidate_ids": [],
            "last_run_timestamp": None
        }

    def _save_progress(self):
        self.progress["last_run_timestamp"] = datetime.now().isoformat()
        os.makedirs(os.path.dirname(self.progress_file), exist_ok=True)
        with open(self.progress_file, "w", encoding="utf-8") as f:
            json.dump(self.progress, f, indent=2)

    def populate(self, limit: Optional[int] = None, batch_size: int = 10, delay_sec: float = 1.0) -> Dict[str, Any]:
        print("=" * 70)
        print("TALENTAI VECTOR EMBEDDINGS POPULATOR (GEMINI 1536-D & PGVECTOR)")
        print("=" * 70)
        
        # Count candidates with and without embeddings
        total_cands = self.db.query(Candidate).count()
        embedded_cands = self.db.query(Candidate).filter(Candidate.embedding.isnot(None)).count()
        missing_cands = total_cands - embedded_cands
        
        print(f"Total Candidates in Database:      {total_cands}")
        print(f"Candidates with Vector Embeddings: {embedded_cands}")
        print(f"Candidates Awaiting Embeddings:    {missing_cands}")
        print(f"Resuming after Candidate ID:       {self.progress['last_processed_candidate_id']}")
        print("-" * 70)

        query = self.db.query(Candidate.id).filter(
            Candidate.embedding.is_(None),
            Candidate.id > self.progress["last_processed_candidate_id"]
        ).order_by(Candidate.id.asc())

        if limit:
            query = query.limit(limit)

        candidate_ids = [r[0] for r in query.all()]
        if not candidate_ids:
            print("[INFO] No pending candidates found to embed.")
            return {
                "total_candidates": total_cands,
                "already_embedded": embedded_cands,
                "processed_in_run": 0
            }

        print(f"Processing batch of {len(candidate_ids)} candidates (batch size {batch_size})...")
        processed_count = 0
        success_count = 0

        for i in range(0, len(candidate_ids), batch_size):
            batch = candidate_ids[i:i + batch_size]
            for cid in batch:
                retry_attempts = 3
                backoff = 2.0
                success = False
                
                while retry_attempts > 0 and not success:
                    try:
                        EmbeddingsService.generate_candidate_embedding(self.db, cid, self.provider)
                        success = True
                        success_count += 1
                        print(f"  [EMBEDDED ID {cid:<5}] Global + Section Vectors Generated & Persisted.")
                    except Exception as e:
                        try:
                            self.db.rollback()
                        except Exception:
                            pass
                        err_str = str(e)
                        if "429" in err_str or "quota" in err_str.lower():
                            print(f"  [QUOTA WARNING] Gemini 429 on ID {cid}, backing off {backoff:.1f}s...")
                            time.sleep(backoff)
                            backoff *= 2
                            retry_attempts -= 1
                        else:
                            print(f"  [ERROR ID {cid}]: {e}")
                            self.progress["failed_candidate_ids"].append(cid)
                            break
                
                processed_count += 1
                self.progress["last_processed_candidate_id"] = cid
                self.progress["total_embeddings_generated"] += 1 if success else 0
                self._save_progress()
                self.db.expire_all()
                time.sleep(delay_sec)

        print("-" * 70)
        print(f"Run completed: Processed {processed_count} candidates, Successfully embedded {success_count}.")
        print("=" * 70)
        return {
            "total_candidates": total_cands,
            "processed_in_run": processed_count,
            "successful_in_run": success_count,
            "progress_file": self.progress_file
        }

    def validate_vector_search(self, test_query: str = "Senior Full Stack Python React Engineer"):
        """Validates that pgvector cosine distance works against live database embeddings."""
        print("\n" + "=" * 70)
        print(f"VALIDATING PGVECTOR COSINE SEARCH: '{test_query}'")
        print("=" * 70)
        
        # 1. Generate query embedding
        q_emb, _ = self.provider.generate_embeddings(test_query)
        if not q_emb or len(q_emb) != 1536:
            raise ValueError(f"Failed to generate valid 1536-dim embedding for query (got {len(q_emb) if q_emb else 0} dims)")
        print(f"[OK] Generated 1536-dim query embedding vector.")

        # 2. Query top candidates using pgvector cosine distance operator <=> via ORM
        distance = Candidate.embedding.cosine_distance(q_emb)
        results = self.db.query(
            Candidate.id,
            Candidate.name,
            Candidate.current_title,
            Candidate.total_experience_years,
            distance.label('dist')
        ).filter(Candidate.embedding.isnot(None)).order_by(distance.asc()).limit(5).all()

        if not results:
            print("[WARNING] Zero candidates returned with vector distance (no embeddings in DB yet).")
            return []

        print(f"[SUCCESS] Top {len(results)} Semantic Matches via pgvector Cosine Distance:")
        for r in results:
            sim = 1.0 - float(r[4])
            print(f"  ID {r[0]:<5} | Sim: {sim:.4f} | Dist: {float(r[4]):.4f} | Name: {r[1]:<25} | Title: {r[2] or 'N/A'} | Exp: {r[3] or 0} yrs")
        print("=" * 70)
        return results

    def close(self):
        self.db.close()

def main():
    parser = argparse.ArgumentParser(description="TalentAI Vector Embedding Populator & Validator")
    parser.add_argument("--limit", type=int, default=10, help="Number of candidates to embed in this run")
    parser.add_argument("--batch-size", type=int, default=5, help="Batch size")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay in seconds between requests")
    parser.add_argument("--validate-only", action="store_true", help="Only run pgvector semantic search validation")
    args = parser.parse_args()

    progress_file = r"D:\recruitment_platform\backend\storage\embedding_progress.json"
    populator = CandidateEmbeddingPopulator(progress_file)

    if not args.validate_only:
        populator.populate(limit=args.limit, batch_size=args.batch_size, delay_sec=args.delay)

    populator.validate_vector_search()
    populator.close()

if __name__ == '__main__':
    main()
