import pytest
import numpy as np
from unittest.mock import MagicMock
from models.all_models import Ontology
from services.candidates.skill_normalizer import SkillNormalizer

@pytest.fixture
def mock_db():
    db = MagicMock()
    # Mock ontology items
    sample_ontologies = [
        Ontology(id=1, canonical_name="Python", category="Programming Languages", aliases=["py", "python3"]),
        Ontology(id=2, canonical_name="React", category="Frontend Development", aliases=["react.js", "reactjs", "react native"]),
        Ontology(id=3, canonical_name="Kubernetes", category="DevOps & Containers", aliases=["k8s", "kube"]),
        Ontology(id=4, canonical_name="Machine Learning", category="AI & Data Science", aliases=["ml", "deep learning", "ai"]),
        Ontology(id=5, canonical_name="FastAPI", category="Backend Development", aliases=["fast-api"]),
    ]
    
    # Pre-populate dummy embeddings for vector test
    v_ml = np.zeros(1536, dtype=np.float32)
    v_ml[0] = 1.0 # arbitrary unit vector for ML
    sample_ontologies[3].embedding = list(v_ml)
    
    db.query().all.return_value = sample_ontologies
    db.query().get.side_effect = lambda cid: next((o for o in sample_ontologies if o.id == cid), None)
    
    # Reset SkillNormalizer cache to use mock db
    SkillNormalizer._cache_initialized = False
    SkillNormalizer._refresh_cache(db)
    return db

def test_exact_match(mock_db):
    orig, can_id = SkillNormalizer.normalize_skill(mock_db, "Python")
    assert orig == "Python"
    assert can_id == 1

def test_case_insensitive_exact_match(mock_db):
    orig, can_id = SkillNormalizer.normalize_skill(mock_db, "react")
    assert orig == "react"
    assert can_id == 2

def test_alias_normalization(mock_db):
    # Test React.js -> React
    _, react_id = SkillNormalizer.normalize_skill(mock_db, "React.js")
    assert react_id == 2
    
    # Test k8s -> Kubernetes
    _, k8s_id = SkillNormalizer.normalize_skill(mock_db, "k8s")
    assert k8s_id == 3
    
    # Test ML & Deep Learning -> Machine Learning
    _, ml_id = SkillNormalizer.normalize_skill(mock_db, "ML")
    assert ml_id == 4
    
    _, dl_id = SkillNormalizer.normalize_skill(mock_db, "Deep Learning")
    assert dl_id == 4

def test_strip_variant_normalization(mock_db):
    _, fid = SkillNormalizer.normalize_skill(mock_db, "FastAPI framework")
    assert fid == 5

def test_vector_similarity_normalization(mock_db):
    # Query with vector close to ML unit vector
    close_vec = np.zeros(1536, dtype=np.float32)
    close_vec[0] = 0.95
    close_vec[1] = 0.05
    close_vec = list(close_vec / np.linalg.norm(close_vec))
    
    class MockVecProvider:
        model_name = "mock-vec"
        def generate_embeddings(self, text):
            return close_vec, {"prompt_tokens": 5, "completion_tokens": 0}
            
    _, can_id = SkillNormalizer.normalize_skill(
        mock_db, 
        "Novel Neural Network Architecture", 
        provider=MockVecProvider()
    )
    assert can_id == 4 # Maps to Machine Learning via vector similarity!

def test_unmatched_skill_returns_none(mock_db):
    class MockVecProvider:
        model_name = "mock-vec"
        def generate_embeddings(self, text):
            # Orthogonal vector (similarity 0.0)
            far_vec = np.zeros(1536, dtype=np.float32)
            far_vec[500] = 1.0
            return list(far_vec), {"prompt_tokens": 5, "completion_tokens": 0}
            
    orig, can_id = SkillNormalizer.normalize_skill(
        mock_db, 
        "Underwater Basket Weaving", 
        provider=MockVecProvider()
    )
    assert orig == "Underwater Basket Weaving"
    assert can_id is None

def test_get_canonical_name(mock_db):
    assert SkillNormalizer.get_canonical_name(mock_db, 2) == "React"
    assert SkillNormalizer.get_canonical_name(mock_db, 3) == "Kubernetes"
    assert SkillNormalizer.get_canonical_name(mock_db, 4) == "Machine Learning"
