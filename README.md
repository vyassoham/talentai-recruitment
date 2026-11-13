# 🏢 TalentAI — Enterprise AI Recruitment & Candidate Matching Platform

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14%2B-black.svg?logo=next.js&logoColor=white)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-336791.svg?logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![PyInstaller](https://img.shields.io/badge/Desktop-PyInstaller%20EXE-FFD43B.svg?logo=windows&logoColor=black)](https://pyinstaller.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

**TalentAI** is an end-to-end, enterprise-grade AI recruiting and resume parsing platform. It combines a **FastAPI** backend with **PostgreSQL + pgvector** for semantic talent discovery, a **Next.js** recruiter dashboard, automated CV extraction, multi-dimensional candidate ranking, and a self-contained **Windows desktop application** bundled with PyInstaller and `pywebview`.

---

## 🌟 Key Features

- **📄 Automated CV Ingestion & Parsing:** Extracts structured work experience, education, skills, and certifications from PDF and DOCX resumes.
- **🧠 Semantic Vector Search (pgvector):** Embeds resumes using `text-embedding-3-small` and performs sub-second similarity queries against job requirement profiles.
- **⚖️ Multi-Factor Candidate Ranking:** Configurable scoring engine balancing:
  - Technical Skill Overlap ($40\%$)
  - Semantic Role Fit ($30\%$)
  - Years of Experience ($20\%$)
  - Preferred Qualifications ($10\%$)
- **🖥️ Standalone Desktop Bundle (`TalentAI.exe`):** Bundles Next.js static assets and local FastAPI daemon into a zero-configuration desktop app via `pywebview`.
- **📱 Android Partner App:** Companion mobile app for on-the-go recruiter notifications and interview management.
- **🛡️ Enterprise Security:** Row-Level Security (RLS) policies, JWT authentication, ClamAV antivirus file scanning, and CORS isolation.

---

## 🏗️ System Architecture

```
                          ┌─────────────────────────────┐
                          │   Recruiter Desktop / Web   │
                          │   (Next.js 14 + PyWebView)  │
                          └──────────────┬──────────────┘
                                         │ REST & WebSockets
                                         ▼
                          ┌─────────────────────────────┐
                          │    FastAPI Application      │
                          │   (Auth, Ingestion, API)    │
                          └──────┬───────────────┬──────┘
                                 │               │
                 ┌───────────────┘               └───────────────┐
                 ▼                                               ▼
     [AI & Embeddings Engine]                       [Data & Storage Layer]
     - Resume Chunking & Parsing                    - PostgreSQL + pgvector
     - OpenAI text-embedding-3-small                - Row-Level Security (RLS)
     - Multi-factor Re-ranking                      - Redis / Celery Task Queue
```

---

## 📂 Repository Structure

```
talentai-recruitment/
├── TalentAI_App.py          # Desktop application entry point (PyWebView + Static Server)
├── TalentAI.spec            # PyInstaller build specification for Windows executable
├── Start_TalentAI.bat       # Quick-start batch launcher for local environment
├── Makefile                 # Automation commands (setup, migrate, test, build)
├── .env.example             # Complete environment configuration template
├── backend/                 # FastAPI REST API, database models, and AI engine
│   ├── app/
│   │   ├── api/             # REST endpoints (auth, candidates, jobs, analytics)
│   │   ├── core/            # Config, security, database sessions
│   │   ├── models/          # SQLAlchemy & pgvector schemas
│   │   └── services/        # CV parser, embedding pipeline, ranking algorithms
├── android/                 # Companion Android mobile application
└── .github/workflows/       # Automated CI/CD pipelines
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.11+
- PostgreSQL 15+ with `pgvector` extension
- Node.js 18+ (for building web assets)

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/vyassoham/talentai-recruitment.git
cd talentai-recruitment

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # On Windows

# Install Python dependencies
pip install -r backend/requirements.txt
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env with your DATABASE_URL and OPENAI_API_KEY
```

### 4. Database Migrations
```bash
alembic upgrade head
```

### 5. Launch the Application
```bash
# To run the desktop application:
python TalentAI_App.py

# Or launch via the Windows batch script:
Start_TalentAI.bat
```

---

## 📦 Building Standalone Desktop Executable

To bundle the entire frontend and backend into a single portable `.exe`:
```bash
pyinstaller TalentAI.spec
```
The compiled output will be generated inside `dist/TalentAI/TalentAI.exe`.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
