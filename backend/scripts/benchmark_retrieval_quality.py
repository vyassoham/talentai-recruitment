import os
import sys
import time
from dotenv import load_dotenv

load_dotenv(r'D:\recruitment_platform\backend\.env')
sys.path.insert(0, r'D:\recruitment_platform\backend')

from core.database import SessionLocal
from services.search.retrieval import HybridRetrievalEngine
from services.search.eligibility import EligibilityEngine
from models.all_models import JobRequirement, Candidate

db = SessionLocal()

BENCHMARK_QUERIES = [
    {
        "role": "Python Backend Engineer",
        "query": "Python FastAPI PostgreSQL Docker Redis",
        "mandatory": ["Python", "FastAPI"],
        "min_exp": 3.0
    },
    {
        "role": "Frontend React Developer",
        "query": "React Next.js TypeScript Tailwind CSS",
        "mandatory": ["React", "TypeScript"],
        "min_exp": 2.0
    },
    {
        "role": "DevOps / Cloud Architect",
        "query": "Kubernetes Docker AWS Terraform CI/CD",
        "mandatory": ["Docker", "Kubernetes"],
        "min_exp": 5.0
    },
    {
        "role": "Data Engineer / PySpark",
        "query": "Apache Spark PySpark Kafka Airflow BigQuery",
        "mandatory": ["Apache Spark", "Airflow"],
        "min_exp": 4.0
    },
    {
        "role": "Full Stack Java Developer",
        "query": "Java Spring Boot Microservices React SQL",
        "mandatory": ["Java", "Spring Boot"],
        "min_exp": 3.0
    },
    {
        "role": "Mobile Engineer (Android/iOS)",
        "query": "Kotlin Android Swift Flutter Mobile Developer",
        "mandatory": ["Kotlin"],
        "min_exp": 2.0
    },
    {
        "role": "Data Scientist / ML Engineer",
        "query": "Machine Learning PyTorch Scikit-learn NLP Python",
        "mandatory": ["Python"],
        "min_exp": 3.0
    },
    {
        "role": "Database Administrator",
        "query": "PostgreSQL MySQL Oracle Database Tuning Backup",
        "mandatory": ["PostgreSQL", "SQL"],
        "min_exp": 5.0
    },
    {
        "role": "QA / Automation Engineer",
        "query": "Selenium Cypress Automation Testing Pytest QA",
        "mandatory": ["Selenium"],
        "min_exp": 2.0
    },
    {
        "role": "Golang Backend Engineer",
        "query": "Golang Go Microservices Docker gRPC",
        "mandatory": ["Go"],
        "min_exp": 2.0
    }
]

print("=" * 75)
print("TALENTAI REPRESENTATIVE SEARCH & RETRIEVAL QUALITY BENCHMARK (10 DOMAINS)")
print("=" * 75)

candidates = db.query(Candidate).order_by(Candidate.id.desc()).limit(250).all()
retrieval_engine = HybridRetrievalEngine(db)

benchmark_results = []

for idx, bq in enumerate(BENCHMARK_QUERIES, 1):
    job = JobRequirement(
        id=str(1000 + idx),
        title=bq["role"],
        raw_description=bq["query"],
        mandatory_skills=[{"canonical_skill_name": s} for s in bq["mandatory"]],
        preferred_skills=[],
        min_experience_years=bq["min_exp"]
    )
    
    t0 = time.time()
    # 1. Eligibility filter
    eligible = EligibilityEngine.filter_eligible_candidates(candidates, job)
    t_elig = time.time() - t0
    
    # 2. Retrieval ranking
    t1 = time.time()
    top_cands = retrieval_engine.retrieve(job, eligible, top_k=5, candidates=candidates)
    t_ret = time.time() - t1
    total_time = time.time() - t0
    
    first_match = top_cands[0] if top_cands else {}
    benchmark_results.append({
        "role": bq["role"],
        "eligible_count": len(eligible),
        "retrieved_count": len(top_cands),
        "top_candidate": first_match.get("name"),
        "top_score": round(first_match.get("retrieval_score", 0.0), 3),
        "latency_sec": round(total_time, 3)
    })
    
    print(f"[{idx:02d}/10] {bq['role']:<32} | Elig: {len(eligible):<3} | Ret: {len(top_cands):<2} | Top: {first_match.get('name', 'None'):<22} | Score: {first_match.get('retrieval_score', 0.0):.3f} | Latency: {total_time:.3f}s")

print("=" * 75)
avg_latency = sum(r["latency_sec"] for r in benchmark_results) / len(benchmark_results)
avg_score = sum(r["top_score"] for r in benchmark_results) / len(benchmark_results)
print(f"Benchmark Summary: 10/10 Queries Processed | Avg Latency: {avg_latency:.3f}s | Avg Top Score: {avg_score:.3f}")
print("=" * 75)

db.close()
