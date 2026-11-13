# TalentAI Internal Operations & Diagnostics Scripts

This directory houses operational, diagnostic, and ad-hoc verification utilities for the TalentAI backend and data pipelines.

## Directory Structure

```
scripts/
├── db/            # Database backfill, migration, deduplication, and repair utilities
├── diagnostics/   # Connectivity, table health, candidate schema, and telemetry inspection
└── adhoc_tests/   # Ad-hoc integration and sanity test scripts for AI, parser, and search
```

## Usage

Ensure your environment variables (or `.env`) are configured and `PYTHONPATH` includes the `backend` directory:

```bash
# Windows PowerShell
$env:PYTHONPATH="backend"
python scripts/diagnostics/check_db_stats.py

# Linux / macOS
PYTHONPATH=backend python scripts/diagnostics/check_db_stats.py
```
