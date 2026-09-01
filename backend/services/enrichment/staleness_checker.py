import datetime
import logging
from typing import List, Dict, Any
from sqlalchemy import or_
from core.database import SessionLocal
from models.all_models import Candidate

logger = logging.getLogger(__name__)

STALENESS_THRESHOLD_DAYS = 90  # Re-enrich profiles older than 90 days


def calculate_staleness_score(candidate) -> float:
    """
    Calculates a staleness score between 0.0 (fresh) and 1.0 (completely stale).
    Based on how long ago the profile was last enriched or updated.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Use last_enriched_at if available, otherwise fall back to updated_at
    reference_date = candidate.last_enriched_at or candidate.updated_at or candidate.created_at
    
    if not reference_date:
        return 1.0  # No date at all = completely stale
        
    if reference_date.tzinfo is None:
        reference_date = reference_date.replace(tzinfo=datetime.timezone.utc)
    
    days_old = (now - reference_date).days
    
    if days_old <= 7:
        return 0.0  # Fresh
    elif days_old <= 30:
        return 0.2  # Slightly aged
    elif days_old <= 90:
        return 0.5  # Getting stale
    elif days_old <= 180:
        return 0.8  # Stale
    else:
        return 1.0  # Very stale


def get_stale_candidates(threshold_days: int = STALENESS_THRESHOLD_DAYS, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Finds candidates whose profiles are stale (not enriched recently).
    Returns a list of candidate info dicts sorted by staleness (most stale first).
    """
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=threshold_days)
    
    with SessionLocal() as db:
        stale_query = db.query(Candidate).filter(
            or_(
                Candidate.last_enriched_at == None,
                Candidate.last_enriched_at < cutoff
            )
        ).order_by(Candidate.updated_at.asc()).limit(limit)
        
        stale_candidates = stale_query.all()
        
        results = []
        for c in stale_candidates:
            staleness = calculate_staleness_score(c)
            results.append({
                "candidate_id": c.id,
                "name": c.name,
                "last_enriched_at": c.last_enriched_at.isoformat() if c.last_enriched_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                "staleness_score": staleness,
                "has_social_links": bool(c.social_links)
            })
        
        return results


def refresh_stale_profiles(threshold_days: int = STALENESS_THRESHOLD_DAYS, limit: int = 20):
    """
    Finds stale candidates and enqueues enrichment background jobs for each.
    This is designed to be called by a scheduled cron or admin API.
    """
    from core.queue import queue_client
    from services.enrichment.web_enrichment import run_full_enrichment
    
    stale = get_stale_candidates(threshold_days=threshold_days, limit=limit)
    
    enqueued = 0
    for candidate_info in stale:
        if not candidate_info["has_social_links"]:
            continue  # Skip candidates without social links
        
        queue_client.enqueue(
            job_type="ENRICHMENT_REFRESH",
            payload={"candidate_id": candidate_info["candidate_id"], "reason": "stale_profile"},
            task_func=run_full_enrichment,
            candidate_id=candidate_info["candidate_id"]
        )
        enqueued += 1
        
    logger.info(f"Staleness refresh: found {len(stale)} stale profiles, enqueued {enqueued} for re-enrichment.")
    return {"stale_found": len(stale), "enqueued": enqueued}


def update_all_staleness_scores():
    """
    Recalculates the staleness_score for all candidates.
    Useful for dashboards and admin views.
    """
    with SessionLocal() as db:
        candidates = db.query(Candidate).all()
        updated = 0
        for c in candidates:
            score = calculate_staleness_score(c)
            c.staleness_score = score
            updated += 1
        db.commit()
        
    return {"updated": updated}
