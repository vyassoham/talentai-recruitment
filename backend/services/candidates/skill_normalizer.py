import logging
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Tuple, Optional, Dict, Any, List
from models.all_models import Ontology

logger = logging.getLogger(__name__)

# Comprehensive technical ontology taxonomy covering AI/ML, Cloud, DevOps, Frontend, Backend, Data, etc.
CANONICAL_ONTOLOGY_SEEDS = [
    # AI & Machine Learning (Addresses: ML, Machine Learning, Deep Learning -> Machine Learning)
    {
        "canonical_name": "Machine Learning",
        "category": "AI & Data Science",
        "aliases": [
            "ml", "deep learning", "dl", "artificial intelligence", "ai",
            "neural networks", "neural net", "statistical learning",
            "supervised learning", "unsupervised learning", "reinforcement learning"
        ]
    },
    {
        "canonical_name": "Large Language Models",
        "category": "AI & Data Science",
        "aliases": [
            "llm", "llms", "generative ai", "genai", "prompt engineering",
            "langchain", "llamaindex", "rag", "retrieval augmented generation",
            "agentic ai", "vector search", "fine-tuning"
        ]
    },
    {
        "canonical_name": "Natural Language Processing",
        "category": "AI & Data Science",
        "aliases": [
            "nlp", "text processing", "sentiment analysis", "spacy", "nltk",
            "huggingface", "transformers", "bert", "text classification"
        ]
    },
    {
        "canonical_name": "Computer Vision",
        "category": "AI & Data Science",
        "aliases": [
            "cv", "image processing", "opencv", "object detection", "yolo",
            "image segmentation", "convolutional neural network", "cnn"
        ]
    },
    {
        "canonical_name": "PyTorch",
        "category": "AI & Data Science",
        "aliases": ["torch", "pytorch lightning", "torchvision"]
    },
    {
        "canonical_name": "TensorFlow",
        "category": "AI & Data Science",
        "aliases": ["tf", "keras", "tensorflow 2.x"]
    },
    {
        "canonical_name": "Data Science",
        "category": "AI & Data Science",
        "aliases": ["data analysis", "predictive modeling", "scikit-learn", "sklearn", "statistical modeling"]
    },
    {
        "canonical_name": "Pandas",
        "category": "AI & Data Science",
        "aliases": ["numpy", "pandas/numpy", "scipy", "dataframes"]
    },

    # Frontend Development (Addresses: React.js -> React)
    {
        "canonical_name": "React",
        "category": "Frontend Development",
        "aliases": [
            "react.js", "reactjs", "react-native", "react native",
            "react 18", "react 17", "react hooks", "redux", "redux toolkit"
        ]
    },
    {
        "canonical_name": "Next.js",
        "category": "Frontend Development",
        "aliases": ["nextjs", "next.js 14", "next 13", "next", "next.js framework"]
    },
    {
        "canonical_name": "Vue.js",
        "category": "Frontend Development",
        "aliases": ["vue", "vuejs", "vue 3", "nuxt", "nuxtjs", "vuex"]
    },
    {
        "canonical_name": "Angular",
        "category": "Frontend Development",
        "aliases": ["angularjs", "angular 2+", "angular.js", "angular 14", "angular framework"]
    },
    {
        "canonical_name": "TypeScript",
        "category": "Programming Languages",
        "aliases": ["ts", "typescript.js", "strict typescript"]
    },
    {
        "canonical_name": "JavaScript",
        "category": "Programming Languages",
        "aliases": ["js", "ecmascript", "es6", "vanilla js", "modern javascript"]
    },
    {
        "canonical_name": "Tailwind CSS",
        "category": "Frontend Development",
        "aliases": ["tailwind", "tailwindcss", "tailwind-css"]
    },
    {
        "canonical_name": "HTML/CSS",
        "category": "Frontend Development",
        "aliases": ["html", "css", "html5", "css3", "sass", "scss", "less"]
    },

    # Backend & Languages
    {
        "canonical_name": "Python",
        "category": "Programming Languages",
        "aliases": ["python3", "py", "cpython", "python 3.x", "asyncio"]
    },
    {
        "canonical_name": "FastAPI",
        "category": "Backend Development",
        "aliases": ["fast-api", "fastapi framework", "uvicorn", "starlette", "pydantic"]
    },
    {
        "canonical_name": "Django",
        "category": "Backend Development",
        "aliases": ["django rest framework", "drf", "django orm"]
    },
    {
        "canonical_name": "Flask",
        "category": "Backend Development",
        "aliases": ["flask framework", "werkzeug"]
    },
    {
        "canonical_name": "Node.js",
        "category": "Backend Development",
        "aliases": ["node", "nodejs", "express", "express.js", "nestjs", "fastify"]
    },
    {
        "canonical_name": "Go",
        "category": "Programming Languages",
        "aliases": ["golang", "go language", "goroutines"]
    },
    {
        "canonical_name": "Rust",
        "category": "Programming Languages",
        "aliases": ["rustlang", "rust-lang", "cargo"]
    },
    {
        "canonical_name": "Java",
        "category": "Programming Languages",
        "aliases": ["java 8", "java 11", "java 17", "spring", "spring boot", "spring framework", "hibernate"]
    },
    {
        "canonical_name": "C++",
        "category": "Programming Languages",
        "aliases": ["cpp", "c/c++", "c plus plus", "modern c++"]
    },
    {
        "canonical_name": "C#",
        "category": "Programming Languages",
        "aliases": ["csharp", ".net", "dotnet", ".net core", "asp.net"]
    },
    {
        "canonical_name": "Ruby",
        "category": "Programming Languages",
        "aliases": ["ruby on rails", "rails"]
    },
    {
        "canonical_name": "PHP",
        "category": "Programming Languages",
        "aliases": ["laravel", "symfony", "wordpress"]
    },

    # Databases & Caching
    {
        "canonical_name": "PostgreSQL",
        "category": "Databases & Storage",
        "aliases": ["postgres", "postgresql with pgvector", "psql", "pgvector", "postgres db"]
    },
    {
        "canonical_name": "MySQL",
        "category": "Databases & Storage",
        "aliases": ["mariadb", "mysql server"]
    },
    {
        "canonical_name": "MongoDB",
        "category": "Databases & Storage",
        "aliases": ["mongo", "nosql mongodb", "mongoose", "documentdb"]
    },
    {
        "canonical_name": "Redis",
        "category": "Databases & Storage",
        "aliases": ["redis cache", "redis pubsub", "key-value store", "redis memory"]
    },
    {
        "canonical_name": "Elasticsearch",
        "category": "Databases & Storage",
        "aliases": ["elastic", "opensearch", "elk", "elk stack"]
    },
    {
        "canonical_name": "SQL",
        "category": "Databases & Storage",
        "aliases": ["relational database", "rdbms", "sql querying", "complex queries", "t-sql"]
    },

    # Cloud, DevOps & Distributed Systems (Addresses: K8s -> Kubernetes)
    {
        "canonical_name": "AWS",
        "category": "Cloud & Infrastructure",
        "aliases": [
            "amazon web services", "ec2", "s3", "lambda", "rds",
            "cloud computing aws", "aws cloud", "dynamodb", "cloudformation"
        ]
    },
    {
        "canonical_name": "GCP",
        "category": "Cloud & Infrastructure",
        "aliases": ["google cloud", "google cloud platform", "bigquery", "gcp cloud", "gke"]
    },
    {
        "canonical_name": "Azure",
        "category": "Cloud & Infrastructure",
        "aliases": ["microsoft azure", "azure cloud", "azure devops", "aks"]
    },
    {
        "canonical_name": "Kubernetes",
        "category": "DevOps & Containers",
        "aliases": [
            "k8s", "kube", "kubernetes clusters", "container orchestration",
            "helm", "k8s deployment", "kubectl"
        ]
    },
    {
        "canonical_name": "Docker",
        "category": "DevOps & Containers",
        "aliases": ["containerization", "docker containers", "dockerfile", "docker-compose"]
    },
    {
        "canonical_name": "CI/CD",
        "category": "DevOps & Containers",
        "aliases": [
            "continuous integration", "github actions", "gitlab ci",
            "jenkins", "argocd", "circleci", "continuous deployment"
        ]
    },
    {
        "canonical_name": "Terraform",
        "category": "DevOps & Containers",
        "aliases": ["infrastructure as code", "iac"]
    },
    {
        "canonical_name": "Kafka",
        "category": "Distributed Systems",
        "aliases": ["apache kafka", "event streaming", "message broker", "kafka streams"]
    },
    {
        "canonical_name": "Celery",
        "category": "Distributed Systems",
        "aliases": ["asynchronous task processing", "celery task queue", "celery/redis", "distributed workers"]
    },
    {
        "canonical_name": "Microservices",
        "category": "Architecture & Systems",
        "aliases": ["distributed systems", "service-oriented architecture", "soa", "microservice architecture"]
    },
    {
        "canonical_name": "REST API",
        "category": "Architecture & Systems",
        "aliases": ["restful api", "rest", "api design", "web services", "json api"]
    },
    {
        "canonical_name": "GraphQL",
        "category": "Architecture & Systems",
        "aliases": ["graphql api", "apollo", "apollo graphql"]
    },
    {
        "canonical_name": "Linux",
        "category": "Operating Systems",
        "aliases": ["unix", "bash", "shell scripting", "ubuntu", "debian", "centos"]
    },
    {
        "canonical_name": "Git",
        "category": "Development Tools",
        "aliases": ["github", "version control", "gitlab", "bitbucket"]
    }
]

class SkillNormalizer:
    """
    Enterprise Skill Normalization & Ontology Engine.
    Maps raw extracted skills (e.g. 'React.js', 'K8s', 'ML', 'Deep Learning')
    to standardized Canonical Ontology skills (e.g. 'React', 'Kubernetes', 'Machine Learning').
    
    4-Tier Architecture:
    - Tier 1: Case-insensitive exact name match
    - Tier 2: Alias dictionary match (e.g. 'react.js' -> 'React', 'k8s' -> 'Kubernetes')
    - Tier 3: Vector Semantic Search using pgvector cosine distance / embedding similarity
              (e.g. 'Deep Learning' or 'Neural Networks' -> 'Machine Learning')
    - Tier 4: Fallback preserves original skill safely without hallucinating links
    """
    
    SIMILARITY_THRESHOLD = 0.72  # Cosine similarity cutoff for vector semantic match
    
    _cache_initialized = False
    _canonical_map: Dict[str, int] = {}
    _alias_map: Dict[str, int] = {}
    _id_to_canonical: Dict[int, str] = {}
    _id_to_category: Dict[int, str] = {}
    _vector_cache: Dict[int, np.ndarray] = {}

    @classmethod
    def _ensure_cache(cls, db: Session):
        """Pre-loads ontology and embeddings into memory for sub-millisecond lookups."""
        if cls._cache_initialized:
            return
            
        cls._refresh_cache(db)

    @classmethod
    def _refresh_cache(cls, db: Session):
        """Reloads ontology cache from database."""
        try:
            ontologies = db.query(Ontology).all()
            
            # If database has few or no records, auto-seed with curated canonical taxonomy
            if len(ontologies) < 20:
                try:
                    cls.seed_ontology(db)
                    ontologies = db.query(Ontology).all()
                except Exception as seed_err:
                    db.rollback()
                    logger.warning(f"Error during auto-seeding ontology: {seed_err}")
                    ontologies = db.query(Ontology).all()
                
            cls._canonical_map.clear()
            cls._alias_map.clear()
            cls._id_to_canonical.clear()
            cls._id_to_category.clear()
            cls._vector_cache.clear()
            
            for ont in ontologies:
                c_name = ont.canonical_name.strip()
                c_lower = c_name.lower()
                
                cls._canonical_map[c_lower] = ont.id
                cls._id_to_canonical[ont.id] = c_name
                cls._id_to_category[ont.id] = ont.category or "Technology"
                
                if ont.aliases and isinstance(ont.aliases, list):
                    for alias in ont.aliases:
                        if isinstance(alias, str):
                            cls._alias_map[alias.strip().lower()] = ont.id
                            
                # Cache embedding vector if present
                if getattr(ont, "embedding", None) is not None:
                    try:
                        emb = np.array(ont.embedding, dtype=np.float32)
                        norm = np.linalg.norm(emb)
                        if norm > 0:
                            cls._vector_cache[ont.id] = emb / norm
                    except Exception:
                        pass
                        
            cls._cache_initialized = True
        except Exception as e:
            try:
                db.rollback()
            except Exception:
                pass
            logger.warning(f"Error initializing SkillNormalizer cache: {e}")

    @classmethod
    def normalize_skill(
        cls, 
        db: Session, 
        raw_skill_name: str, 
        provider: Optional[Any] = None
    ) -> Tuple[str, Optional[int]]:
        """
        Maps a raw skill name to a canonical skill in the ontology.
        Returns (original_skill, canonical_skill_id).
        Does NOT over-normalize distinct technologies (e.g., Python != Django).
        """
        if not raw_skill_name:
            return raw_skill_name, None
            
        cls._ensure_cache(db)
        clean_name = raw_skill_name.strip()
        lower_name = clean_name.lower()
        
        # -------------------------------------------------------------
        # Tier 1: Exact Match
        # -------------------------------------------------------------
        if lower_name in cls._canonical_map:
            return raw_skill_name, cls._canonical_map[lower_name]

        # -------------------------------------------------------------
        # Tier 2: Alias & Common Variation Match
        # -------------------------------------------------------------
        if lower_name in cls._alias_map:
            return raw_skill_name, cls._alias_map[lower_name]

        # Check common strip patterns (e.g. "React.js" -> "react", "NodeJS" -> "node")
        normalized_variant = lower_name.replace(".js", "").replace("js", "").replace(" framework", "").strip()
        if normalized_variant and normalized_variant in cls._canonical_map:
            return raw_skill_name, cls._canonical_map[normalized_variant]
        if normalized_variant and normalized_variant in cls._alias_map:
            return raw_skill_name, cls._alias_map[normalized_variant]

        # -------------------------------------------------------------
        # Tier 3: Vector Semantic Search (Embeddings)
        # -------------------------------------------------------------
        try:
            ai_provider = provider
            if ai_provider is None:
                from services.ai.provider import get_ai_provider
                ai_provider = get_ai_provider()
                
            from services.ai.provider import MockProvider
            if ai_provider and not isinstance(ai_provider, MockProvider):
                # 3a. Generate embedding for query skill
                query_vec, _ = ai_provider.generate_embeddings(clean_name)
                
                if query_vec and len(query_vec) > 0:
                    q_arr = np.array(query_vec, dtype=np.float32)
                    q_norm = np.linalg.norm(q_arr)
                    
                    if q_norm > 0:
                        q_unit = q_arr / q_norm
                        
                        # Compare against cached normalized canonical vectors
                        best_id = None
                        best_sim = -1.0
                        
                        for ont_id, can_unit in cls._vector_cache.items():
                            sim = float(np.dot(q_unit, can_unit))
                            if sim > best_sim:
                                best_sim = sim
                                best_id = ont_id
                                
                        if best_sim >= cls.SIMILARITY_THRESHOLD and best_id is not None:
                            logger.info(
                                f"Vector Normalization: '{raw_skill_name}' -> "
                                f"'{cls._id_to_canonical.get(best_id)}' (Cosine Similarity: {best_sim:.3f})"
                            )
                            return raw_skill_name, best_id
                            
                        # 3b. Try pgvector query directly on database if vector cache was empty
                        if not cls._vector_cache:
                            row = db.execute(
                                text(
                                    "SELECT id, canonical_name, (embedding <=> CAST(:vec AS vector)) AS distance "
                                    "FROM ontology "
                                    "WHERE embedding IS NOT NULL "
                                    "ORDER BY distance ASC "
                                    "LIMIT 1;"
                                ),
                                {"vec": str(query_vec)}
                            ).fetchone()
                            
                            if row:
                                ont_id, can_name, distance = row
                                # Cosine distance = 1 - cosine_similarity. Threshold: distance <= (1 - 0.72) = 0.28
                                if distance <= (1.0 - cls.SIMILARITY_THRESHOLD):
                                    logger.info(
                                        f"pgvector DB Normalization: '{raw_skill_name}' -> "
                                        f"'{can_name}' (Distance: {distance:.3f})"
                                    )
                                    return raw_skill_name, ont_id
        except Exception as e:
            logger.debug(f"Vector search skill normalization bypassed: {e}")

        # -------------------------------------------------------------
        # Tier 4: Fallback
        # -------------------------------------------------------------
        return raw_skill_name, None

    @classmethod
    def get_canonical_name(cls, db: Session, canonical_id: int) -> Optional[str]:
        """Returns the human-readable canonical skill name for a given ontology ID."""
        cls._ensure_cache(db)
        if canonical_id in cls._id_to_canonical:
            return cls._id_to_canonical[canonical_id]
            
        ont = db.query(Ontology).get(canonical_id)
        if ont:
            cls._id_to_canonical[ont.id] = ont.canonical_name
            return ont.canonical_name
        return None

    @classmethod
    def seed_ontology(cls, db: Session, provider: Optional[Any] = None) -> int:
        """
        Seeds or updates the database ontology with canonical skills,
        aliases, categories, and precomputed embeddings.
        """
        count_updated = 0
        
        # Phase 1: Fast insert/update of canonical names and aliases
        for item in CANONICAL_ONTOLOGY_SEEDS:
            name = item["canonical_name"]
            cat = item["category"]
            aliases = item["aliases"]
            
            existing = db.query(Ontology).filter(Ontology.canonical_name.ilike(name)).first()
            if existing:
                existing.category = cat
                existing.aliases = aliases
                count_updated += 1
            else:
                new_ont = Ontology(
                    canonical_name=name,
                    category=cat,
                    aliases=aliases
                )
                db.add(new_ont)
                count_updated += 1
                
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to commit canonical skill seeds: {e}")
            return 0

        # Phase 2: Compute embeddings for skills missing vector representation
        ai_provider = provider
        if ai_provider is None:
            try:
                from services.ai.provider import get_ai_provider, MockProvider
                p = get_ai_provider()
                if not isinstance(p, MockProvider):
                    ai_provider = p
            except Exception:
                ai_provider = None

        if ai_provider:
            try:
                unembedded = db.query(Ontology).filter(Ontology.embedding == None).all()
                for ont in unembedded:
                    try:
                        emb, _ = ai_provider.generate_embeddings(ont.canonical_name)
                        if emb:
                            ont.embedding = emb
                    except Exception as emb_err:
                        logger.debug(f"Failed generating embedding for '{ont.canonical_name}': {emb_err}")
                db.commit()
            except Exception as e:
                db.rollback()
                logger.debug(f"Failed committing ontology embeddings: {e}")

        return count_updated

