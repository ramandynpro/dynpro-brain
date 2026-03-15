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
- choose workflow: `expert_finder`, `interviewer_finder`, `client_domain_finder`, `poc_support_finder`, or `pod_builder`
- enter a request like: `Need a data engineering lead for BFSI modernization work`
- add skill filter: `Data Engineering`
- optionally set structured filters: `internal/external`, `country`, `timezone`, `practice`, `client name`, `domain name`, `worked with person name`, `prefer people who worked together`, `minimum available percent`, `max bill rate`, `budget band`, `interviewer only`, `minimum prior interview count`, `POC support only`, `minimum client-facing comfort`, `minimum POC participation count`, and `available by date`

The backend applies these structured filters directly to the sample JSON records before ranking and returning results. Client/domain filtering checks assignment/project history first, and also uses person-level `top_clients` and `top_domains` when present. Availability gives a small ranking boost to people who are more available sooner. Budget fit also gives a small ranking boost when a person is comfortably within the selected budget constraints. Client/domain relevance gives a small ranking boost and is called out in recommendation explanations when it changes rank. Relationship edges from `relationship_edge.json` now also add a small ranking boost when you provide `worked with person name` (or the API `worked_with_person_id`) and a candidate has `worked_with` evidence linked to that person. When interviewer search is relevant, interviewer readiness also gives a small ranking boost and is called out in the explanation. For POC support finder workflows, POC readiness (willingness, prior POC/presales participation, and client-facing comfort) now also gives a small ranking boost and is called out in the explanation.

There is also a simple **confidence layer** on each recommendation (kept separate from ranking logic):
- `confidence_score`: transparent score using evidence count, evidence confidence, evidence freshness, and whether `last_verified_at` is present
- `confidence_band`: `high`, `medium`, or `low`
- `evidence_count`: number of workflow-tagged evidence records used
- `freshness_summary`: plain-English freshness readout for supporting evidence
- `source_mix`: simple count of source types involved in the recommendation context

The explanation text now includes confidence/freshness context so reviewers can quickly see when stale or sparse evidence lowers trust.

For Phase 1 privacy, UI recommendations keep commercial output light and use budget-fit wording instead of exposing raw commercial details.

You will see recommendation(s) built from the sample JSON files in `data/sample_json/` with:
- confidence band and freshness summary
- why recommended
- evidence IDs
- uncertainties
- next action


## Pilot request logging and feedback (Phase 1 simple)

To support pilot usage, the backend now writes two local JSONL logs (no production infra):
- `data/pilot_request_log.jsonl`
- `data/pilot_feedback_log.jsonl`

What gets logged after each search/pod run:
- request_id
- timestamp
- workflow
- input summary
- result count
- top result ids
- confidence summary (when available)

Feedback capture is intentionally tiny for Phase 1:
- request_id
- useful_yes_no
- trust_rating (1-5)
- notes
- missed_person_or_gap

API endpoints:
- `POST /api/v1/pilot/feedback` to submit feedback
- `GET /api/v1/pilot/recent` to list recent request logs with feedback summaries

In Streamlit, after running a search, the latest `request_id` is shown in a small feedback form so pilot users can quickly submit trust/usefulness notes.

## Notes

- This is **not** production-ready.
- No auth yet (intentionally out of scope).
- No automatic staffing decisions.
- Search logic now reads from local sample JSON through a simple ingestion loader (still pre-database).


## Pod builder v1 (new in Phase 1)

You can now run a simple **pod_builder** workflow for small team recommendations.

In the UI, choose workflow `pod_builder` and provide:
- required skills
- desired roles
- pod size
- internal/external preference
- budget ceiling

What pod builder v1 does (simple and explainable):
- picks a small set of people from sample JSON
- tries to maximize required skill coverage and desired role coverage
- respects existing filters where possible (location/timezone/practice/client/domain/availability/budget guardrails)
- checks availability and budget in a lightweight Phase 1 way
- if `prefer people who worked together` is checked, it adds a small tie-breaker boost for people with prior `worked_with` relationship edges

What the response includes:
- recommended people
- simple role assignment where possible
- coverage summary
- budget-fit summary
- gaps
- substitutions/backups
- explainability fields (why selected, satisfied constraints, partially satisfied constraints, uncertainties, next action)

Important: this is still decision support only. A delivery lead should review pod suggestions before staffing decisions.
