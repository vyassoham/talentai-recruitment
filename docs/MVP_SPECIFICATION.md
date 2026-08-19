# Final MVP Implementation Specification — AI-Powered Recruitment Automation Platform

## 1. Objective

Build a production-shaped MVP of an AI-powered recruitment platform that can ingest candidate CVs, understand job requirements, retrieve relevant candidates, deeply evaluate them, validate the AI's conclusions, and present an evidence-based ranking to recruiters.

The MVP must prove the complete recruitment intelligence loop:

**CV ingestion → CV parsing → normalization → embeddings → JD parsing → eligibility filtering → hybrid retrieval → AI reranking → evidence validation → explainable ranking → recruiter feedback → evaluation**

The architecture must be designed so the MVP can later scale from hundreds of CVs to millions without requiring a fundamental rewrite.

---

# 2. Core Architecture Principles

### Principle 1 — Deterministic systems handle facts

Use conventional code/database logic wherever the answer can be calculated reliably.

Examples:

* Years of experience
* Employment date calculations
* Mandatory requirement filtering
* Location constraints
* Duplicate detection
* Candidate availability
* Required certifications
* Numeric thresholds
* Date ranges

Do not ask an LLM to perform calculations that can be performed deterministically.

### Principle 2 — Retrieval systems maximize recall

Use multiple retrieval mechanisms:

* PostgreSQL filtering
* Full-text search
* Canonical skill ontology
* Fuzzy matching
* pgvector semantic search

The objective of retrieval is to avoid missing potentially relevant candidates.

### Principle 3 — AI handles contextual interpretation

Use AI for tasks where context and semantic interpretation matter:

* Understanding ambiguous job requirements
* Interpreting CV evidence
* Determining contextual relevance of experience
* Comparing candidate experience with nuanced requirements
* Producing explanations

AI must not invent evidence.

### Principle 4 — Every important AI decision must be auditable

Store:

* Model provider
* Model name/version
* Prompt version
* Pipeline version
* Input hash
* Timestamp
* Structured input
* Structured output
* Evidence
* Confidence
* Validation result

### Principle 5 — "Insufficient evidence" is valid

The system must never force a Yes/No answer when the CV does not contain sufficient evidence.

Possible states include:

* `MEETS`
* `PARTIALLY_MEETS`
* `DOES_NOT_MEET`
* `INSUFFICIENT_EVIDENCE`

---

# 3. End-to-End Pipeline

```text
                    JOB DESCRIPTION
                           │
                           ▼
                    ┌─────────────┐
                    │   JD Parser │
                    └──────┬──────┘
                           │
                           ▼
              Structured Job Requirements
                           │
                 ┌─────────┴─────────┐
                 │                   │
             Mandatory            Preferred
                 │                   │
                 └─────────┬─────────┘
                           ▼
                 ┌───────────────────┐
                 │ Eligibility Layer │
                 │ Deterministic     │
                 └─────────┬─────────┘
                           │
                     Eligible Pool
                           │
                           ▼
                 ┌───────────────────┐
                 │ Hybrid Retrieval  │
                 │ SQL + Skills +    │
                 │ pgvector          │
                 └─────────┬─────────┘
                           │
                        Top K
                           │
                           ▼
                 ┌───────────────────┐
                 │   AI Reranker     │
                 │ Deep Evaluation   │
                 └─────────┬─────────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │ Evidence Validator│
                 └─────────┬─────────┘
                           │
                           ▼
                 Explainable Ranking
                           │
                           ▼
                 ┌───────────────────┐
                 │ Recruiter UI      │
                 └─────────┬─────────┘
                           │
                           ▼
                 Recruiter Feedback
                           │
                           ▼
                 Evaluation Dataset
```

---

# 4. Repository Structure

Use a monorepo with clear separation between application layers.

```text
recruitment-platform/
│
├── backend/
│   ├── api/
│   ├── core/
│   ├── models/
│   ├── repositories/
│   ├── services/
│   │   ├── ai/
│   │   ├── documents/
│   │   ├── search/
│   │   └── jobs/
│   ├── workers/
│   ├── tests/
│   └── main.py
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── tests/
│
├── evaluation/
│   ├── dataset/
│   ├── benchmark.py
│   └── reports/
│
├── infrastructure/
│   └── docker/
│
├── docker-compose.yml
├── .env.example
├── README.md
└── Makefile
```

---

# 5. Candidate Data Model

The candidate model should separate raw source information from normalized information.

Minimum entities:

### Candidate

* ID
* Name
* Contact information
* Location
* Total experience
* Relevant experience
* Current title
* Current company
* Availability
* Source
* Created timestamp
* Updated timestamp

### CandidateSkill

* Candidate ID
* Canonical skill ID
* Original extracted skill
* Skill category
* Evidence references
* Years of experience where determinable
* Last-used date where determinable
* Confidence

### Employment

* Candidate ID
* Company
* Job title
* Start date
* End date
* Description
* Extracted skills
* Evidence references

### CandidateDocument

* Candidate ID
* Original filename
* Storage reference
* MIME type
* File hash
* Extraction status
* Parsing status
* Embedding status

Never store uploaded CV binaries directly inside PostgreSQL.

---

# 6. Job Requirement Model

Represent a job requirement as structured data.

Each requirement should contain:

```text
requirement_id
category
canonical_skill
original_text
requirement_type
minimum_experience
maximum_experience
importance
evidence_required
```

Where:

`requirement_type`

can be:

* `MANDATORY`
* `PREFERRED`

And the requirement state can later contain:

* `MEETS`
* `PARTIALLY_MEETS`
* `DOES_NOT_MEET`
* `INSUFFICIENT_EVIDENCE`

The original JD text must always be retained alongside the structured interpretation.

---

# 7. Skill Ontology

Create a canonical skill system.

Example:

```text
Python
 ├── Py
 ├── Python 3
 └── CPython

Django REST Framework
 ├── DRF
 └── Django REST

Amazon Web Services
 ├── AWS
 ├── Amazon AWS
 └── AWS Cloud
```

The ontology should support:

* Aliases
* Synonyms
* Parent/child relationships
* Categories
* Versions
* Related technologies
* Canonical IDs

Do not assume that related technologies are equivalent.

For example:

`Python` ≠ `Django`

`AWS` ≠ `Kubernetes`

`React` ≠ `React Native`

Semantic similarity may identify related technologies, but deterministic matching must preserve these distinctions.

---

# 8. CV Ingestion Pipeline

Uploading a CV should trigger an asynchronous workflow:

```text
Upload
  ↓
File Validation
  ↓
Virus/Security Check
  ↓
Document Extraction
  ↓
Text Normalization
  ↓
CV Parsing
  ↓
Skill Normalization
  ↓
Experience Calculation
  ↓
Candidate Deduplication
  ↓
Embedding Generation
  ↓
Database Indexing
```

The system should support at least:

* PDF
* DOCX

The original document must be retained while extracted structured information is stored separately.

Failures must be recoverable and visible.

Example:

```text
Extraction Failed
Parsing Failed
Embedding Failed
Indexing Failed
```

should be represented explicitly rather than silently failing.

---

# 9. Job Parsing Pipeline

When a recruiter submits a JD:

```text
Raw JD
  ↓
Text normalization
  ↓
AI extraction
  ↓
Skill normalization
  ↓
Requirement classification
  ↓
Validation
  ↓
Structured Job Requirement
```

The parser should identify:

* Role
* Seniority
* Mandatory skills
* Preferred skills
* Experience requirements
* Education
* Certifications
* Location
* Work arrangement
* Domain/industry requirements
* Other constraints

The system should preserve the original text associated with every extracted requirement.

---

# 10. Stage 1 — Eligibility Engine

This stage should be deterministic.

Example:

```text
if required_experience > candidate_relevant_experience:
    candidate = ineligible

if mandatory_location_required:
    verify_location()

if mandatory_certification_required:
    verify_certification()
```

However, requirements that cannot be reliably determined from structured data should not automatically eliminate candidates.

For example:

> "Strong system-design experience"

may require semantic/AI evaluation.

Therefore, requirements should be classified as:

* Deterministically evaluable
* Semantically evaluable
* AI/contextually evaluable

This prevents overly aggressive filtering.

---

# 11. Stage 2 — Hybrid Retrieval

Retrieve candidates using multiple signals.

### Structured retrieval

Use PostgreSQL for:

* Experience
* Location
* Availability
* Canonical skills
* Certifications
* Other hard attributes

### Semantic retrieval

Use pgvector embeddings for:

* Overall experience similarity
* Project similarity
* Responsibility similarity
* Domain relevance
* Semantic skill/context matching

### Skill retrieval

Use the ontology for:

* Aliases
* Synonyms
* Normalized technologies
* Related terminology

Combine these signals into a retrieval score.

The retrieval layer should return approximately the top **100–500 candidates**, depending on dataset size and configuration.

---

# 12. Stage 3 — AI Reranking

Only the retrieved candidates should undergo expensive deep analysis.

For every candidate, generate structured output such as:

```json
{
  "overall_score": 94,
  "requirements": [
    {
      "requirement": "Python 6+ years",
      "status": "MEETS",
      "evidence": [
        {
          "source": "employment",
          "text_reference": "Senior Python Developer, 2019-2025"
        }
      ],
      "confidence": 0.96
    }
  ]
}
```

The model must not be permitted to produce unsupported evidence.

---

# 13. Evidence Validation

The validator should independently check whether the reranker's conclusions are supported by the candidate's source data.

For example:

```text
AI says:
"Candidate has 7 years of Python."

Structured CV data:
Python experience = 4.5 years

Result:
VALIDATION FAILURE
```

The candidate should then be flagged rather than silently displaying the unsupported claim.

This validation layer is a critical component of system trust.

---

# 14. Ranking

Do not make the final ranking simply equal to an LLM-generated score.

The final ranking should combine multiple controlled signals.

Conceptually:

```text
Final Score =
    Eligibility
  + Mandatory Requirement Coverage
  + Relevant Experience
  + Skill Match
  + Semantic Relevance
  + Preferred Requirement Coverage
  + Evidence Confidence
  - Validation Penalties
```

The exact weighting should be configurable and evaluated empirically.

The system must also enforce:

> A candidate failing a genuinely mandatory requirement cannot outrank a candidate who satisfies all mandatory requirements merely because of strong preferred-skill similarity.

---

# 15. Recruiter Dashboard

The recruiter should see:

### Search

* Job description input
* Structured requirement preview
* Mandatory/preferred breakdown
* Search button
* Search status

### Candidate results

For every candidate:

* Candidate name
* Overall score
* Mandatory requirements
* Preferred requirements
* Relevant experience
* Key matched skills
* Missing skills
* Evidence confidence
* Validation status

### Candidate detail

Show:

```text
94% Match

Mandatory Requirements
✓ Python — Meets
✓ Django — Meets
✓ 6+ years — Meets

Preferred Requirements
✓ AWS — Strong match
~ Kubernetes — Partial

Insufficient Evidence
? Fintech experience

Evidence
"Senior Python Developer..."
"Built Django REST APIs..."
```

The UI should make it possible for a recruiter to verify the AI's conclusion rather than blindly trust it.

---

# 16. Recruiter Feedback

Every result should allow feedback.

Examples:

* Strong match
* Good match
* Weak match
* False positive
* Missing required skill
* Wrong experience
* Excellent candidate
* Rejected
* Shortlisted

Feedback should be stored independently from the candidate profile.

This data becomes valuable for:

* Evaluation
* Ranking improvements
* Prompt improvements
* Future model training
* Personalization

---

# 17. AI Provider Abstraction

Define an interface such as:

```text
parse_jd()
parse_cv()
generate_embedding()
evaluate_candidate()
validate_evidence()
```

The business logic must never directly depend on a specific AI provider.

Provider implementations can include:

```text
OpenAIProvider
GeminiProvider
AnthropicProvider
LocalModelProvider
MockProvider
```

Configuration determines which provider is active.

---

# 18. Model Registry

Every AI operation must record:

```text
provider
model
model_version
embedding_model
prompt_version
pipeline_version
input_hash
timestamp
latency
token_usage
estimated_cost
```

This is essential for reproducibility and cost management.

---

# 19. Async Processing

The system should expose a generic queue interface:

```text
enqueue()
get_status()
retry()
cancel()
```

The underlying implementation may initially use Redis/Celery, but application code should depend on the interface rather than directly on Celery.

Long-running operations must not block HTTP requests.

Example:

```text
POST /candidates/upload
        ↓
202 Accepted
        ↓
job_id
        ↓
background processing
        ↓
GET /jobs/{job_id}
```

---

# 20. Evaluation Framework

Create a fixed benchmark dataset containing:

* Job descriptions
* Candidate CVs
* Human relevance labels
* Expected rankings
* Mandatory requirements
* Preferred requirements

Run the complete pipeline against this dataset.

Measure:

* Precision@10
* Recall@10
* NDCG@10
* Mandatory-requirement violation rate
* False-positive rate
* False-negative rate
* Ranking agreement
* Search latency
* End-to-end latency
* AI cost per JD
* Validation failure rate

The benchmark should produce a machine-readable report and human-readable summary.

---

# 21. Testing Strategy

### Unit tests

Test:

* Experience calculations
* Skill normalization
* Eligibility rules
* Date calculations
* Ranking formulas
* API contracts
* Provider interfaces

### Integration tests

Test:

```text
Upload CV
→ Parse
→ Normalize
→ Embed
→ Store
→ Search
```

and:

```text
JD
→ Parse
→ Eligibility
→ Retrieval
→ Reranking
→ Validation
→ Ranking
```

### AI tests

Use deterministic mock providers to test pipeline behavior without relying on live model APIs.

### Regression tests

Every change to prompts, models, ranking logic, or ontology should be benchmarked against the evaluation dataset.

---

# 22. Security Requirements

Because the platform handles candidate PII and CV documents, implement security from the MVP.

Minimum requirements:

* Authentication interface
* Authorization interface
* Role-based access control foundation
* Encrypted transport
* Secure file storage
* File type validation
* File size limits
* Audit logging
* PII-aware logging
* Data deletion capability
* Secrets through environment/secret management
* No CV contents in application logs

Do not expose uploaded CV files through predictable public URLs.

---

# 23. MVP Acceptance Criteria

The MVP is considered successful only when all of the following work end-to-end.

### Candidate ingestion

* Upload at least 50–100 CVs.
* Parse PDF/DOCX documents.
* Extract structured candidate information.
* Generate embeddings.
* Index candidates successfully.
* Handle ingestion failures visibly.

### Job processing

* Submit a real JD.
* Extract structured requirements.
* Correctly distinguish mandatory and preferred requirements.
* Normalize skills using the ontology.

### Search

* Apply deterministic eligibility rules.
* Perform hybrid retrieval.
* Return a meaningful candidate pool.
* Rank candidates using the configured retrieval signals.

### AI evaluation

* Deeply evaluate the top candidates.
* Produce structured evidence.
* Produce confidence scores.
* Support `INSUFFICIENT_EVIDENCE`.
* Validate AI conclusions against source data.

### Recruiter experience

* Display ranked candidates.
* Explain why each candidate ranked where they did.
* Display missing requirements.
* Display supporting evidence.
* Capture recruiter feedback.

### Evaluation

* Run the benchmark dataset.
* Produce Precision@10, Recall@10, NDCG@10 and other agreed metrics.
* Track AI cost and latency.
* Detect mandatory-requirement violations.

---

# 24. Definition of Done

Do not consider the MVP complete merely because:

> "The frontend loads and the APIs return data."

The MVP is complete when a recruiter can perform this complete workflow:

**Upload CVs → create JD → parse requirements → search candidates → evaluate candidates → inspect evidence → shortlist → provide feedback → measure ranking quality.**

The system must demonstrate that the AI is not merely generating attractive explanations; it is producing **measurably useful candidate rankings grounded in actual CV evidence**.

---

# 25. Future Scaling Path

The MVP should leave clear extension points for:

* Millions of candidates
* Distributed ingestion
* Dedicated search clusters
* Advanced vector infrastructure
* Multiple embedding models
* Model routing
* Reranking models
* Learning-to-rank
* Recruiter personalization
* Candidate deduplication at scale
* ATS integrations
* CRM integrations
* Automated outreach
* Interview scheduling
* Candidate lifecycle automation
* Continuous evaluation
* Human-in-the-loop learning

The MVP should **not prematurely implement all of these features**.

The immediate objective is to build one extremely reliable vertical slice of the recruitment intelligence engine and establish measurable performance baselines.

---

# Final Implementation Principle

Build the system around this division of responsibility:

**Code determines facts.**

**Search retrieves possibilities.**

**AI interprets context.**

**Validation challenges AI conclusions.**

**Evidence explains decisions.**

**Human recruiters remain the decision-makers.**

**Evaluation measures whether the system is actually improving recruitment outcomes.**

This architecture should be implemented as the baseline before adding broader automation, integrations, or enterprise-scale infrastructure.
