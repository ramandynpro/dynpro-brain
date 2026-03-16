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



## Leadership demo mode (Phase 1)

Use this when you want a simple leadership walkthrough without changing ranking logic.

1. Start backend and frontend as in steps 3 and 4 above.
2. In the Streamlit app, switch **View** to **Leadership Demo**.
3. Choose one of the five canned scenarios:
   - Expert Finder
   - Interviewer Finder
   - Client/Domain Finder
   - POC Support Finder
   - Pod Builder
4. Click **Run Demo Scenario** to execute the existing backend using a prefilled realistic request.
5. Review the leadership-friendly output:
   - request summary
   - top recommendation or pod
   - why it was recommended
   - confidence/freshness summary
   - constraints applied
   - next action
6. Use **Current Pilot KPIs** in the same view to show live pilot metrics from `/api/v1/pilot/kpi-summary`.

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
- `GET /api/v1/pilot/kpi-summary` to get a simple pilot KPI snapshot

The KPI snapshot includes:
- total requests
- requests by workflow
- average trust rating
- useful yes rate
- recent missed-person/gap count
- pod builder request count
- interviewer finder request count
- optional duration summary only when duration data exists in feedback notes (using `duration_minutes=<number>` format)

In Streamlit, after running a search, the latest `request_id` is shown in a small feedback form so pilot users can quickly submit trust/usefulness notes.
There is also a simple **Pilot Admin View (Phase 1)** at the bottom of the app that shows KPI summary, recent requests, and recent feedback.

## Data quality dashboard (Phase 1 hardening)

A small data quality summary endpoint is now available for pilot hardening:
- `GET /api/v1/pilot/data-quality`

What it checks (kept transparent and simple):
- missing required profile fields
- missing timezone/country/practice
- missing availability fields
- missing commercial fields
- low-confidence profiles (default threshold: `0.6`)
- stale profiles based on `last_verified_at` (default threshold: `90` days)
- simple related-data coverage counts and missing person-link checks for assignment/project, skill-evidence, relationship edges, and commercial profiles

You can tune the endpoint using query params:
- `stale_profile_days` (default `90`)
- `low_confidence_threshold` (default `0.6`)
- `example_limit` (default `10`)

In Streamlit, switch **View** to **Data Quality** to see:
- summary counts
- stale profile count
- low-confidence count
- missing-field counts
- related data coverage
- a short list of example problematic records


## Pilot CSV intake template and importer (Phase 1 simple)

This is a local-only pilot intake utility to load real pilot people data into the existing canonical `person.json` shape.

### CSV columns to use

Use `data/pilot_csv/pilot_intake_template.csv` as your starter file.

Required core columns (must be present and populated on each row):
- `person_id`
- `full_name`
- `current_role`
- `home_location`
- `timezone`
- `internal_external`
- `practice`
- `source_type`
- `source_system`
- `source_record_id`

Recommended optional columns:
- `summary`
- `interviewer_suitable`
- `willing_to_interview`
- `prior_interview_count`
- `client_facing_comfort`
- `top_clients` (use `|` between values)
- `top_domains` (use `|` between values)
- `willing_to_support_pocs`
- `poc_participation_count`
- `presales_participation_count`
- `profile_confidence`
- `profile_last_updated_at`
- `last_verified_at`

A ready-to-copy example with 4 rows is in `data/pilot_csv/example_pilot_people.csv`.

### How to import a pilot CSV file

From the repo root:

```bash
python -m backend.app.services.pilot_csv_importer \
  --input data/pilot_csv/example_pilot_people.csv \
  --output data/sample_json/person.imported.json
```

What this importer does (and keeps simple for Phase 1):
- reads a local CSV file only
- validates required columns and required values
- returns friendly row-level errors when a core field is missing or malformed
- maps rows to the existing canonical person JSON shape
- preserves `source_provenance` and `last_verified_at` when provided

No auth, no production infrastructure, and no ETL pipeline are added.

## Run search with imported pilot people data (Phase 1 simple)

By default, search reads people from `data/sample_json/person.json`.

If you also want search to use imported pilot people:

1. Import a pilot CSV to JSON (example):

```bash
python -m backend.app.services.pilot_csv_importer \
  --input data/pilot_csv/example_pilot_people.csv \
  --output data/sample_json/person.imported.json
```

2. Start backend with optional pilot people path set:

```bash
DYNPRO_PILOT_PEOPLE_PATH=data/sample_json/person.imported.json uvicorn backend.app.main:app --reload
```


## Pilot assignment/project CSV intake and importer (Phase 1 simple)

This is a local-only pilot intake utility to load real assignment/project history into the existing canonical `assignment_project.json` shape.

### CSV columns to use

Use `data/pilot_csv/assignment_project_intake_template.csv` as your starter file.

Required columns (must be present and populated on each row):
- `assignment_id`
- `person_id`
- `client`
- `project_name`
- `role`

Recommended optional columns:
- `domain`
- `start_date`
- `end_date`
- `project_summary`
- `confidence`
- `source_type`
- `source_system`
- `source_record_id`

A ready-to-copy example with 4 rows is in `data/pilot_csv/example_pilot_assignment_project.csv`.

### How to import a pilot assignment/project CSV file

From the repo root:

```bash
python -m backend.app.services.pilot_assignment_csv_importer \
  --input data/pilot_csv/example_pilot_assignment_project.csv \
  --output data/sample_json/assignment_project.imported.json
```

What this importer does (kept simple for Phase 1):
- reads a local CSV file only
- validates required columns and values with friendly row-level errors
- maps rows into the canonical assignment/project JSON fields (`project_id`, `client_name`, `role_on_project`)
- keeps source provenance fields for explainability

No auth, no production infrastructure, and no ETL pipeline are added.


## Pilot skill-evidence CSV intake and importer (Phase 1 simple)

This is a local-only pilot intake utility to load real skill evidence into the existing canonical `skill_evidence.json` shape.

### CSV columns to use

Use `data/pilot_csv/skill_evidence_intake_template.csv` as your starter file.

Required columns (must be present and populated on each row):
- `skill_evidence_id`
- `person_id`
- `skill`
- `source`
- `confidence`

Recommended optional columns:
- `evidence_text`
- `observed_at`
- `workflow_tags` (use `|` between values, defaults to `expert_finder|interviewer_finder|pod_builder`)
- `validated_by`

A ready-to-copy example with 6 rows is in `data/pilot_csv/example_pilot_skill_evidence.csv`.

### How to import a pilot skill-evidence CSV file

From the repo root:

```bash
python -m backend.app.services.pilot_skill_evidence_csv_importer \
  --input data/pilot_csv/example_pilot_skill_evidence.csv \
  --output data/sample_json/skill_evidence.imported.json
```

What this importer does (kept simple for Phase 1):
- reads a local CSV file only
- validates required columns and values with friendly row-level errors
- maps rows into the canonical skill evidence JSON fields (`evidence_id`, `skill_name`, `source_uri`)
- keeps workflow tags and provenance-ready metadata for explainability

No auth, no production infrastructure, and no ETL pipeline are added.


## Pilot commercial-profile CSV intake and importer (Phase 1 simple)

This is a local-only pilot intake utility to load real commercial profile data into the existing canonical `commercial_profile.json` shape for budget-fit support.

### CSV columns to use

Use `data/pilot_csv/commercial_profile_intake_template.csv` as your starter file.

Required columns (must be present and populated on each row):
- `commercial_id`
- `person_id`
- `engagement_model`
- `currency`
- `cost_rate` or `cost_rate_band`
- `bill_rate` or `target_bill_rate`

Recommended optional columns:
- `bill_rate_band`
- `availability_percent`
- `availability_note`
- `effective_from`
- `confidence`
- `source_type`
- `source_system`
- `source_record_id`

A ready-to-copy example with 4 rows is in `data/pilot_csv/example_pilot_commercial_profile.csv`.

### How to import a pilot commercial-profile CSV file

From the repo root:

```bash
python -m backend.app.services.pilot_commercial_csv_importer \
  --input data/pilot_csv/example_pilot_commercial_profile.csv \
  --output data/sample_json/commercial_profile.imported.json
```

What this importer does (kept simple for Phase 1):
- reads a local CSV file only
- validates required columns and values with friendly row-level errors
- maps rows into the canonical commercial profile JSON fields
- keeps source provenance fields for explainability

No auth, no production infrastructure, and no ETL pipeline are added.

## Pilot relationship-edge CSV intake and importer (Phase 1 simple)

This is a local-only pilot intake utility to load relationship-edge evidence into the existing canonical `relationship_edge.json` shape.

### CSV columns to use

Use `data/pilot_csv/relationship_edge_intake_template.csv` as your starter file.

Required columns (must be present and populated on each row):
- `edge_id`
- `from_person_id`
- `to_person_id`
- `relationship_type`

Optional columns:
- `context`
- `strength`
- `confidence`
- `source_type`
- `source_system`
- `source_record_id`
- `last_verified_at`

A ready-to-copy example with 4 rows is in `data/pilot_csv/example_pilot_relationship_edge.csv`.

### How to import a pilot relationship-edge CSV file

From the repo root:

```bash
python -m backend.app.services.pilot_relationship_csv_importer \
  --input data/pilot_csv/example_pilot_relationship_edge.csv \
  --output data/sample_json/relationship_edge.imported.json
```

What this importer does (kept simple for Phase 1):
- reads a local CSV file only
- validates required columns and values with friendly row-level errors
- maps rows into the canonical relationship-edge JSON fields
- keeps source provenance fields for explainability

No auth, no production infrastructure, and no ETL pipeline are added.

## Run search with imported pilot people, assignment/project, skill-evidence, commercial, and relationship-edge data (Phase 1 simple)

By default, search reads from:
- `data/sample_json/person.json`
- `data/sample_json/assignment_project.json`
- `data/sample_json/commercial_profile.json`
- `data/sample_json/relationship_edge.json`

If you want search/ranking to include imported pilot files alongside sample data:

1. Import pilot people CSV (example):

```bash
python -m backend.app.services.pilot_csv_importer \
  --input data/pilot_csv/example_pilot_people.csv \
  --output data/sample_json/person.imported.json
```

2. Import pilot assignment/project CSV (example):

```bash
python -m backend.app.services.pilot_assignment_csv_importer \
  --input data/pilot_csv/example_pilot_assignment_project.csv \
  --output data/sample_json/assignment_project.imported.json
```

3. Import pilot skill-evidence CSV (example):

```bash
python -m backend.app.services.pilot_skill_evidence_csv_importer \
  --input data/pilot_csv/example_pilot_skill_evidence.csv \
  --output data/sample_json/skill_evidence.imported.json
```

4. Import pilot commercial-profile CSV (example):

```bash
python -m backend.app.services.pilot_commercial_csv_importer \
  --input data/pilot_csv/example_pilot_commercial_profile.csv \
  --output data/sample_json/commercial_profile.imported.json
```

5. Import pilot relationship-edge CSV (example):

```bash
python -m backend.app.services.pilot_relationship_csv_importer \
  --input data/pilot_csv/example_pilot_relationship_edge.csv \
  --output data/sample_json/relationship_edge.imported.json
```

6. Start backend with optional pilot file paths:

```bash
DYNPRO_PILOT_PEOPLE_PATH=data/sample_json/person.imported.json \
DYNPRO_PILOT_ASSIGNMENTS_PATH=data/sample_json/assignment_project.imported.json \
DYNPRO_PILOT_SKILL_EVIDENCE_PATH=data/sample_json/skill_evidence.imported.json \
DYNPRO_PILOT_COMMERCIAL_PATH=data/sample_json/commercial_profile.imported.json \
DYNPRO_PILOT_RELATIONSHIP_PATH=data/sample_json/relationship_edge.imported.json \
uvicorn backend.app.main:app --reload
```

In results, the UI now shows a tiny data-source note for people data, assignment/project data, skill evidence data, and commercial-profile data: sample, pilot, or sample + pilot.

Optional configuration knobs:
- `DYNPRO_SAMPLE_DATA_DIR` (default: `data/sample_json`)
- `DYNPRO_PILOT_PEOPLE_PATH` (optional local JSON file from people importer)
- `DYNPRO_PILOT_ASSIGNMENTS_PATH` (optional local JSON file from assignment/project importer)
- `DYNPRO_PILOT_SKILL_EVIDENCE_PATH` (optional local JSON file from skill-evidence importer)
- `DYNPRO_PILOT_COMMERCIAL_PATH` (optional local JSON file from commercial-profile importer)
- `DYNPRO_PILOT_RELATIONSHIP_PATH` (optional local JSON file from relationship-edge importer)

Simple behavior when both files are present:
- search uses sample + pilot people together, sample + pilot assignment/project data together, sample + pilot skill evidence together, and sample + pilot commercial-profile data together, and sample + pilot relationship-edge data together
- if the same `person_id` exists in people files, the pilot person record replaces the sample person record
- if the same `assignment_id`/`project_id` exists in assignment/project files, the pilot assignment/project record replaces the sample one
- if the same `evidence_id` exists in skill-evidence files, the pilot skill-evidence record replaces the sample one
- if the same `commercial_profile_id`/`commercial_id` exists in commercial files, the pilot commercial record replaces the sample one
- if the same `edge_id` exists in relationship-edge files, the pilot relationship-edge record replaces the sample one
- recommendations still use the same confidence/freshness logic and source provenance fields

In the Streamlit UI, small data-source notes show whether people, assignment/project context, skill evidence, and commercial profile data used sample data, pilot data, or both.

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


## Phase 1 governance mode (simple commercial masking)

This MVP now has a **local viewer mode** selector in Streamlit (no auth, no real permissions system):
- `broad_user`
- `commercial_aware`

How it works:
- `broad_user` mode keeps recommendations and explainability fully active, but masks exact raw commercial rate fields in the UI.
  - Recommendation quality, confidence, freshness, and evidence explanations still appear.
  - Pod and budget sections use budget-fit wording / budget bands instead of exact rate numbers.
  - Cards include a note when commercial details are intentionally masked.
- `commercial_aware` mode shows the existing detailed commercial values already used by the app.

This is intentionally a small Phase 1 governance layer only:
- no auth
- no production permission system
- no ranking redesign
