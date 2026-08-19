import os
import requests
import logging
from typing import List, Dict, Any, Optional
from core.database import SessionLocal
from models.all_models import Candidate, CandidateSkill, Ontology
from services.ai.provider import get_ai_provider
from services.candidates.skill_normalizer import SkillNormalizer

logger = logging.getLogger(__name__)


class PassiveSourcer:
    """
    Discovers passive candidates from public APIs (GitHub, StackOverflow).
    Unlike our ingestion pipeline (which processes uploaded CVs), this actively
    searches the open web for talent that matches a given skill profile.
    """
    
    @staticmethod
    def search_github(language: str, location: str = None, min_repos: int = 5, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Uses the GitHub Search API to find developers by programming language and location.
        Returns a list of discovered candidate profiles.
        """
        token = os.getenv("GITHUB_TOKEN")
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"token {token}"
        
        # Build search query
        query_parts = [f"language:{language}", f"repos:>={min_repos}"]
        if location:
            query_parts.append(f"location:{location}")
        
        query = " ".join(query_parts)
        
        try:
            resp = requests.get(
                f"https://api.github.com/search/users?q={query}&per_page={max_results}&sort=repositories",
                headers=headers,
                timeout=15
            )
            resp.raise_for_status()
            results = resp.json()
            
            discovered = []
            for user in results.get("items", []):
                # Fetch full profile
                from core.security import SecurityUtils
                user_url = user.get("url")
                if not user_url or not SecurityUtils.is_safe_url(user_url):
                    continue
                profile_resp = requests.get(user_url, headers=headers, timeout=10)
                if profile_resp.status_code != 200:
                    continue
                    
                profile = profile_resp.json()
                
                discovered.append({
                    "name": profile.get("name") or profile.get("login"),
                    "email": profile.get("email"),
                    "location": profile.get("location"),
                    "bio": profile.get("bio", ""),
                    "github_url": profile.get("html_url"),
                    "public_repos": profile.get("public_repos", 0),
                    "followers": profile.get("followers", 0),
                    "primary_language": language,
                    "source": "GITHUB_SOURCING"
                })
            
            return discovered
            
        except Exception as e:
            logger.error(f"GitHub passive sourcing failed: {e}")
            return []
    
    @staticmethod
    def search_stackoverflow(tags: List[str], min_reputation: int = 1000, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Uses the StackOverflow API to find top answerers for specific technology tags.
        """
        discovered = []
        
        for tag in tags[:3]:  # Limit API calls
            try:
                resp = requests.get(
                    f"https://api.stackexchange.com/2.3/tags/{tag}/top-answerers/all_time?site=stackoverflow&pagesize={max_results}",
                    timeout=10
                )
                if resp.status_code != 200:
                    continue
                
                data = resp.json()
                for item in data.get("items", []):
                    user = item.get("user", {})
                    if user.get("reputation", 0) < min_reputation:
                        continue
                    
                    discovered.append({
                        "name": user.get("display_name", "Unknown"),
                        "email": None,
                        "location": user.get("location"),
                        "bio": f"StackOverflow Top Answerer for [{tag}]. Reputation: {user.get('reputation', 0)}. Answer Score: {item.get('score', 0)}",
                        "stackoverflow_url": user.get("link"),
                        "reputation": user.get("reputation", 0),
                        "primary_tag": tag,
                        "source": "STACKOVERFLOW_SOURCING"
                    })
                    
            except Exception as e:
                logger.error(f"StackOverflow sourcing for tag '{tag}' failed: {e}")
        
        return discovered
    
    @staticmethod
    def ingest_discovered_candidates(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Takes a list of discovered candidates from passive sourcing and creates
        Candidate records in the database. Deduplicates by email or GitHub URL.
        """
        provider = get_ai_provider()
        created = 0
        skipped = 0
        
        with SessionLocal() as db:
            for c in candidates:
                # Deduplication check
                if c.get("email"):
                    existing = db.query(Candidate).filter(Candidate.email == c["email"]).first()
                    if existing:
                        skipped += 1
                        continue
                
                # Check by name + source (rough dedup for sourceable candidates)
                if c.get("name"):
                    existing = db.query(Candidate).filter(
                        Candidate.name == c["name"],
                        Candidate.source == c.get("source")
                    ).first()
                    if existing:
                        skipped += 1
                        continue
                
                # Build social links
                social_links = {}
                if c.get("github_url"):
                    social_links["github"] = c["github_url"]
                if c.get("stackoverflow_url"):
                    social_links["stackoverflow"] = c["stackoverflow_url"]
                
                # Generate embedding from bio
                bio_text = c.get("bio", "") or c.get("name", "")
                embedding, _ = provider.generate_embeddings(bio_text)
                
                candidate = Candidate(
                    name=c.get("name"),
                    email=c.get("email"),
                    location=c.get("location"),
                    social_links=social_links,
                    source=c.get("source", "PASSIVE_SOURCING"),
                    embedding=embedding
                )
                db.add(candidate)
                db.flush()
                
                # Add primary skill if known
                primary = c.get("primary_language") or c.get("primary_tag")
                if primary:
                    orig, can_id = SkillNormalizer.normalize_skill(db, primary)
                    skill = CandidateSkill(
                        candidate_id=candidate.id,
                        canonical_skill_id=can_id,
                        original_extracted_skill=orig
                    )
                    db.add(skill)
                
                created += 1
            
            db.commit()
        
        return {"created": created, "skipped_duplicates": skipped}
