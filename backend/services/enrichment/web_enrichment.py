import os
import re
import requests
import logging
from pydantic import BaseModel
from core.database import SessionLocal
from models.all_models import Candidate
from services.ai.provider import get_ai_provider

logger = logging.getLogger(__name__)

class EnrichmentAudit(BaseModel):
    audit_summary: str
    score: float

# ==================== StackOverflow Enrichment ====================
def enrich_stackoverflow(job_id: str, candidate_id: int):
    """
    Fetches the candidate's StackOverflow profile via the public API.
    Extracts their reputation, top tags, and answer count.
    Sends this to the LLM for an audit.
    """
    with SessionLocal() as db:
        candidate = db.get(Candidate, candidate_id)
        if not candidate or not candidate.social_links:
            return {"status": "skipped", "reason": "No social links"}
        
        so_url = None
        links = candidate.social_links or {}
        for key, url in links.items():
            if isinstance(url, str) and "stackoverflow.com" in url.lower():
                so_url = url
                break
        
        if not so_url:
            return {"status": "skipped", "reason": "No StackOverflow link"}
        
        # Extract user ID: https://stackoverflow.com/users/12345/username -> 12345
        match = re.search(r'stackoverflow\.com/users/(\d+)', so_url)
        if not match:
            return {"status": "failed", "reason": "Could not parse SO user ID"}
        
        user_id = match.group(1)
        
        try:
            resp = requests.get(
                f"https://api.stackexchange.com/2.3/users/{user_id}?site=stackoverflow&filter=default",
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            
            if not data.get("items"):
                return {"status": "failed", "reason": "SO user not found"}
            
            user = data["items"][0]
            reputation = user.get("reputation", 0)
            display_name = user.get("display_name", "Unknown")
            
            # Fetch top tags
            tags_resp = requests.get(
                f"https://api.stackexchange.com/2.3/users/{user_id}/top-tags?site=stackoverflow&pagesize=5",
                timeout=10
            )
            top_tags = []
            if tags_resp.status_code == 200:
                tags_data = tags_resp.json()
                for tag in tags_data.get("items", []):
                    top_tags.append(f"{tag['tag_name']} (score: {tag.get('answer_score', 0)})")
            
            so_summary = (
                f"StackOverflow Profile: {display_name}\n"
                f"Reputation: {reputation}\n"
                f"Top Tags: {', '.join(top_tags) if top_tags else 'None'}\n"
            )
            
            # LLM Audit
            provider = get_ai_provider()
            prompt = (
                f"Evaluate this candidate's StackOverflow presence.\n"
                f"A reputation above 1000 is solid, above 10000 is expert-level.\n"
                f"Provide an audit_summary (2-3 sentences) and a score (0.0-1.0).\n\n"
                f"{so_summary}"
            )
            audit, _ = provider.generate_structured(prompt, EnrichmentAudit, "You are a technical recruiter evaluating community contributions.")
            
            # Append to existing evidence
            existing = candidate.external_evidence or ""
            candidate.external_evidence = existing + f"\n\n[StackOverflow] {audit.audit_summary}"
            db.commit()
            
            return {"status": "completed", "so_reputation": reputation, "score": audit.score}
            
        except Exception as e:
            logger.error(f"StackOverflow enrichment failed for candidate {candidate_id}: {e}")
            return {"status": "failed", "error": str(e)}


# ==================== Google Scholar Enrichment ====================
def enrich_google_scholar(job_id: str, candidate_id: int):
    """
    For research-oriented candidates. Fetches their Google Scholar profile 
    via the Semantic Scholar API (free, no key needed) if they have a Scholar URL.
    Falls back to searching by name.
    """
    with SessionLocal() as db:
        candidate = db.get(Candidate, candidate_id)
        if not candidate or not candidate.social_links:
            return {"status": "skipped", "reason": "No social links"}
        
        scholar_url = None
        links = candidate.social_links or {}
        for key, url in links.items():
            if isinstance(url, str) and ("scholar.google" in url.lower() or "semanticscholar" in url.lower()):
                scholar_url = url
                break
        
        if not scholar_url and not candidate.name:
            return {"status": "skipped", "reason": "No Scholar link or name"}
        
        try:
            # Use Semantic Scholar API (free, rate-limited)
            if scholar_url and "semanticscholar.org" in scholar_url:
                # Extract author ID
                match = re.search(r'author/(\d+)', scholar_url)
                if match:
                    author_id = match.group(1)
                    resp = requests.get(f"https://api.semanticscholar.org/graph/v1/author/{author_id}?fields=name,hIndex,citationCount,paperCount", timeout=10)
                else:
                    return {"status": "failed", "reason": "Could not parse Scholar ID"}
            else:
                # Search by name
                search_name = candidate.name
                resp = requests.get(f"https://api.semanticscholar.org/graph/v1/author/search?query={search_name}&limit=1", timeout=10)
                if resp.status_code == 200:
                    results = resp.json()
                    if results.get("data") and len(results["data"]) > 0:
                        author_id = results["data"][0]["authorId"]
                        resp = requests.get(f"https://api.semanticscholar.org/graph/v1/author/{author_id}?fields=name,hIndex,citationCount,paperCount", timeout=10)
                    else:
                        return {"status": "skipped", "reason": "No Scholar profile found for name"}
                else:
                    return {"status": "failed", "reason": f"Scholar API error: {resp.status_code}"}
            
            if resp.status_code != 200:
                return {"status": "failed", "reason": f"Scholar API returned {resp.status_code}"}
            
            author = resp.json()
            h_index = author.get("hIndex", 0)
            citations = author.get("citationCount", 0)
            papers = author.get("paperCount", 0)
            
            scholar_summary = (
                f"Scholar Profile: {author.get('name', 'Unknown')}\n"
                f"h-index: {h_index}, Citations: {citations}, Papers: {papers}\n"
            )
            
            provider = get_ai_provider()
            prompt = (
                f"Evaluate this candidate's research profile.\n"
                f"An h-index above 10 is solid, above 30 is world-class.\n"
                f"Provide an audit_summary (2-3 sentences) and a score (0.0-1.0).\n\n"
                f"{scholar_summary}"
            )
            audit, _ = provider.generate_structured(prompt, EnrichmentAudit, "You are a research talent evaluator.")
            
            existing = candidate.external_evidence or ""
            candidate.external_evidence = existing + f"\n\n[Google Scholar] {audit.audit_summary}"
            db.commit()
            
            return {"status": "completed", "h_index": h_index, "score": audit.score}
            
        except Exception as e:
            logger.error(f"Scholar enrichment failed for candidate {candidate_id}: {e}")
            return {"status": "failed", "error": str(e)}


# ==================== Design Portfolio Enrichment ====================
def enrich_design_portfolio(job_id: str, candidate_id: int):
    """
    For designers. Checks for Dribbble or Behance links and fetches their portfolio stats.
    Uses Dribbble's public endpoint or Behance API.
    """
    with SessionLocal() as db:
        candidate = db.get(Candidate, candidate_id)
        if not candidate or not candidate.social_links:
            return {"status": "skipped", "reason": "No social links"}
        
        portfolio_url = None
        platform = None
        links = candidate.social_links or {}
        for key, url in links.items():
            if isinstance(url, str):
                if "dribbble.com" in url.lower():
                    portfolio_url = url
                    platform = "Dribbble"
                    break
                elif "behance.net" in url.lower():
                    portfolio_url = url
                    platform = "Behance"
                    break
        
        if not portfolio_url:
            return {"status": "skipped", "reason": "No design portfolio link"}
        
        try:
            # Extract username from URL
            username = portfolio_url.rstrip("/").split("/")[-1]
            
            portfolio_summary = f"Design Portfolio ({platform}): {username}\nURL: {portfolio_url}\n"
            portfolio_summary += "Note: Portfolio was detected and linked. Manual review of visual work is recommended."
            
            provider = get_ai_provider()
            prompt = (
                f"A candidate has a {platform} portfolio at {portfolio_url}.\n"
                f"Based on the platform presence alone, provide a brief audit_summary noting that the candidate " 
                f"actively maintains a design portfolio, and a conservative score (0.5-0.7 range since we cannot " 
                f"visually evaluate the designs via API).\n"
            )
            audit, _ = provider.generate_structured(prompt, EnrichmentAudit, "You are a design talent evaluator.")
            
            existing = candidate.external_evidence or ""
            candidate.external_evidence = existing + f"\n\n[{platform}] {audit.audit_summary}"
            db.commit()
            
            return {"status": "completed", "platform": platform, "score": audit.score}
            
        except Exception as e:
            logger.error(f"Design enrichment failed for candidate {candidate_id}: {e}")
            return {"status": "failed", "error": str(e)}


# ==================== Master Enrichment Dispatcher ====================
def run_full_enrichment(job_id: str, candidate_id: int):
    """
    Master dispatcher that runs ALL enrichment checks for a candidate.
    Called as a background task after CV ingestion.
    """
    from services.enrichment.github_auditor import run_github_audit
    
    results = {}
    results["github"] = run_github_audit(job_id=job_id, candidate_id=candidate_id)
    results["stackoverflow"] = enrich_stackoverflow(job_id=job_id, candidate_id=candidate_id)
    results["scholar"] = enrich_google_scholar(job_id=job_id, candidate_id=candidate_id)
    results["design"] = enrich_design_portfolio(job_id=job_id, candidate_id=candidate_id)
    
    # Update last_enriched_at
    import datetime
    with SessionLocal() as db:
        candidate = db.get(Candidate, candidate_id)
        if candidate:
            candidate.last_enriched_at = datetime.datetime.now(datetime.timezone.utc)
            db.commit()
    
    return results
