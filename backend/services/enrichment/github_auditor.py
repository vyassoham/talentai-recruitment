import os
import requests
from sqlalchemy.orm import Session
from core.database import SessionLocal
from models.all_models import Candidate
from services.ai.provider import get_ai_provider

def run_github_audit(job_id: str, candidate_id: int):
    """
    Background worker function that takes a candidate, checks if they have a GitHub link,
    fetches their repositories and recent commits, and uses the LLM to audit their code quality.
    """
    with SessionLocal() as db:
        candidate = db.get(Candidate, candidate_id)
        if not candidate or not candidate.social_links:
            return {"status": "skipped", "reason": "No social links"}
            
        github_url = candidate.social_links.get("github")
        if not github_url:
            # Let's also check for github.com in the dict values in case key is different
            for url in candidate.social_links.values():
                if isinstance(url, str) and "github.com" in url.lower():
                    github_url = url
                    break
                    
        if not github_url:
            return {"status": "skipped", "reason": "No GitHub link found"}
            
        # Extract username
        # e.g., https://github.com/torvalds -> torvalds
        parts = github_url.rstrip("/").split("/")
        username = parts[-1]
        
        token = os.getenv("GITHUB_TOKEN")
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"token {token}"
            
        # 1. Fetch public repos
        try:
            from core.security import SecurityUtils
            target_url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page=3"
            if not SecurityUtils.is_safe_url(target_url):
                return {"status": "failed", "error": "SSRF blocked unsafe URL"}
                
            repos_resp = requests.get(target_url, headers=headers, timeout=10)
            repos_resp.raise_for_status()
            repos = repos_resp.json()
            
            repo_summaries = []
            for repo in repos:
                repo_name = repo["name"]
                lang = repo.get("language")
                desc = repo.get("description", "No description")
                
                # Try to fetch recent commits
                commits_url = f"https://api.github.com/repos/{username}/{repo_name}/commits?per_page=3"
                commits_info = []
                if SecurityUtils.is_safe_url(commits_url):
                    commits_resp = requests.get(commits_url, headers=headers, timeout=10)
                    if commits_resp.status_code == 200:
                        commits = commits_resp.json()
                        for commit in commits:
                            msg = commit["commit"]["message"]
                            commits_info.append(f"- {msg}")
                        
                repo_str = f"Repo: {repo_name} ({lang})\nDescription: {desc}\nRecent Commits:\n" + "\n".join(commits_info)
                repo_summaries.append(repo_str)
                
            if not repo_summaries:
                candidate.external_evidence = "GitHub profile found but no public repositories or commits available."
                db.commit()
                return {"status": "completed", "reason": "No public repos"}
                
            raw_github_data = "\n\n".join(repo_summaries)
            
            # 2. LLM Code Audit
            provider = get_ai_provider()
            system_prompt = "You are a Principal Software Engineer. Audit this candidate's open-source GitHub footprint."
            prompt = (
                f"Please review the following GitHub activity for a candidate.\n"
                f"Evaluate their code quality, commit message habits, and language proficiency.\n"
                f"Provide a brief 3-4 sentence qualitative summary, and then an 'overall_engineering_score' between 0.0 and 1.0.\n"
                f"Format your response as strict JSON: {{\"audit_summary\": \"...\", \"score\": 0.85}}\n\n"
                f"GitHub Data:\n{raw_github_data}"
            )
            
            # Use Pydantic to ensure structured output
            from pydantic import BaseModel
            class AuditOutput(BaseModel):
                audit_summary: str
                score: float
                
            audit_result, _ = provider.generate_structured(prompt, AuditOutput, system_prompt)
            
            candidate.external_evidence = audit_result.audit_summary
            candidate.engineering_quality_score = audit_result.score
            db.commit()
            
            return {"status": "completed", "audit_score": audit_result.score}
            
        except Exception as e:
            # If GitHub API fails (e.g. rate limit, or invalid username), fail gracefully
            candidate.external_evidence = f"Failed to audit GitHub: {str(e)}"
            db.commit()
            return {"status": "failed", "error": str(e)}
