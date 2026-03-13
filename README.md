# DynPro Brain (Phase 1 MVP Scaffold)

This repository now contains a **practical scaffold** for DynPro Brain as an internal capability intelligence engine.

It is intentionally small and focused on foundations:
- structured data + semantic-ready retrieval
- source provenance + freshness + confidence
- explainability-ready response shape
- human review in the loop

## What is included

- `backend/` - Python FastAPI skeleton with a search endpoint and explainable response model
- `frontend/` - lightweight Streamlit app skeleton for running a search and showing explainability fields
- `db/schema/` - PostgreSQL + pgvector schema scripts and a simple capability snapshot view
- `data/sample_json/` - sample JSON documents for core Phase 1 entities
- `db/seeds/README.md` - simple seed-loading approach placeholder
- `BUILD_PLAN.md` - what was created and what should come next
- `object_store_placeholder/` - placeholder folder for future document/object storage integration

## Quick start (plain English)

## 1) Create Python environments

Backend:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Frontend:
```bash
cd frontend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) Start PostgreSQL

Use any local Postgres instance and create a database named `dynpro_brain`.

Then run schema scripts in order:
```bash
psql postgresql://postgres:postgres@localhost:5432/dynpro_brain -f db/schema/001_extensions.sql
psql postgresql://postgres:postgres@localhost:5432/dynpro_brain -f db/schema/002_tables.sql
psql postgresql://postgres:postgres@localhost:5432/dynpro_brain -f db/schema/003_views.sql
```

## 3) Run backend API

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

API will be at `http://localhost:8000`.

## 4) Run frontend app

```bash
cd frontend
source .venv/bin/activate
streamlit run app.py
```

UI will open in your browser (usually `http://localhost:8501`).

## 5) Try a sample search

In the UI:
- choose workflow: `expert_finder`
- enter a request like: `Need a data engineering lead for BFSI modernization work`
- add skill filter: `Data Engineering`
- optionally set structured filters: `internal/external`, `country`, `timezone`, `practice`, `client name`, `domain name`, `minimum available percent`, `max bill rate`, `budget band`, `interviewer only`, `minimum prior interview count`, and `available by date`

The backend applies these structured filters directly to the sample JSON records before ranking and returning results. Client/domain filtering checks assignment/project history first, and also uses person-level `top_clients` and `top_domains` when present. Availability gives a small ranking boost to people who are more available sooner. Budget fit also gives a small ranking boost when a person is comfortably within the selected budget constraints. Client/domain relevance gives a small ranking boost and is called out in recommendation explanations when it changes rank. When interviewer search is relevant, interviewer readiness also gives a small ranking boost and is called out in the explanation.

For Phase 1 privacy, UI recommendations keep commercial output light and use budget-fit wording instead of exposing raw commercial details.

You will see recommendation(s) built from the sample JSON files in `data/sample_json/` with:
- why recommended
- evidence IDs
- uncertainties
- next action

## Notes

- This is **not** production-ready.
- No auth yet (intentionally out of scope).
- No automatic staffing decisions.
- Search logic now reads from local sample JSON through a simple ingestion loader (still pre-database).
