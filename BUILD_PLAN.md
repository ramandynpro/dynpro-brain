# BUILD_PLAN (Phase 1 Scaffold)

## What was created now

1. **Repo structure for MVP foundations**
   - Added clear folders for backend, frontend, database schema, sample data, and object storage placeholder.

2. **Python backend skeleton**
   - FastAPI app with:
     - health endpoint
     - `POST /api/v1/search` endpoint
   - Explainability-ready response model includes:
     - confidence score
     - why recommended
     - evidence IDs
     - uncertainties
     - next action
   - Stub ranking service to keep logic simple and reviewable.

3. **Lightweight frontend skeleton**
   - Streamlit app to submit query + filters and display explainability fields from API response.

4. **Database/schema foundation**
   - PostgreSQL scripts for:
     - extensions (`vector`, `pg_trgm`)
     - core tables: person, skill_evidence, assignment_project, commercial_profile, relationship_edge
     - basic indexes including vector index
     - a snapshot view for person capability overview

5. **Sample JSON files**
   - Added one sample record for each requested entity type:
     - person
     - skill evidence
     - assignment/project
     - commercial profile
     - relationship edge

## What to build next (small, practical steps)

1. Add a small ingestion script to load `data/sample_json/*.json` into Postgres.
2. Add simple lexical + structured filtering in backend search.
3. Add semantic retrieval step using pgvector embeddings for skill evidence.
4. Add score breakdown fields in API (`structured_score`, `semantic_score`, `relationship_score`).
5. Add a review workflow state field (`needs_human_review`) in responses.
6. Add basic tests for API models and ranking output schema.

## What owner should review next

1. Confirm table names and fields for internal data reality.
2. Confirm explainability response fields are right for decision-support users.
3. Confirm first workflow priority (`expert_finder`) before implementing real ranking.
