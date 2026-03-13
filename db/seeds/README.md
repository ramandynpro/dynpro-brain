# Seed Strategy (Phase 1)

Keep ingestion simple:
1. Start with JSON files under `data/sample_json/`.
2. Build a small Python loader later (`backend/scripts/load_json.py`).
3. Preserve source provenance and `updated_at` timestamps during load.

No automatic enrichment yet.
