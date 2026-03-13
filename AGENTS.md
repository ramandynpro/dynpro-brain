# DynPro Brain - AGENT INSTRUCTIONS

## What this project is
Build DynPro Brain as an internal capability intelligence engine.
This is a decision-support product, not a simple resume search app.

Think in terms of:
- knowledge
- evidence
- constraints
- recommendations
- explainability
- trust

## Phase 1 goal
Build a practical MVP only.

Primary workflows for now:
1. expert finder
2. interviewer finder
3. client/domain finder
4. pod builder
5. POC support finder

Do not jump to phase-2 or phase-3 intelligence features unless explicitly asked.

## Product rules
Always follow these principles:
- structured data and semantic data must coexist
- raw documents are evidence, not final truth
- every recommendation must be explainable
- human review is required for consequential decisions
- freshness matters
- commercial feasibility matters

## Anti-patterns to avoid
Do not build:
- raw vector search only
- black-box scoring
- hidden assumptions
- one giant unstructured person blob
- performance surveillance features
- broad exposure of sensitive commercial data
- fake “current” answers from stale data

## MVP architecture preference
Prefer a simple phase-1 stack:
- Python backend
- Postgres
- pgvector or equivalent vector support
- object storage for documents
- simple relationship/graph tables
- lightweight web app

Do not over-engineer phase 1.

## Search and ranking approach
Use hybrid retrieval and ranking:
- structured filters
- semantic retrieval
- lexical matching
- relationship/graph signals

Ranking should consider:
- skill relevance
- domain relevance
- client relevance
- evidence freshness
- confidence
- location/timezone fit
- availability
- cost/budget fit
- relationship context
- role/seniority suitability

## Canonical entities
Design around these core entities:
- person
- skill evidence
- assignment/project
- relationship edge
- commercial profile
- availability profile

## Engineering rules
Always:
- preserve source provenance
- keep last-updated timestamps
- support confidence scoring
- make corrections easy
- keep auditability from the start
- make JSON ingestion simple
- design for incremental enrichment

## User experience rules
The product should support:
- direct search
- filters
- profile cards
- conversational requests
- recommendation explanations
- scenario comparison later

For every recommendation or answer, show:
- recommended result
- why it was recommended
- what evidence supports it
- what uncertainties remain
- what next action the user can take

## Scope guardrails
For the first build, do not implement:
- automatic staffing decisions
- deep automation
- live scheduling
- performance analytics
- all-source ingestion

## Working style for this repo
Because the project owner prefers copy-paste and plain English:
- explain your plan in simple language
- keep changes small and reviewable
- prefer one logical step at a time
- when making changes, clearly list:
  - which files you changed
  - what you added
  - what the owner should review next

If requirements are ambiguous, choose the simplest practical MVP path that matches these instructions.
