from datetime import UTC, datetime

from app.models.search import Recommendation, SearchQuery


def rank_people_for_query(query: SearchQuery) -> list[Recommendation]:
    """
    Stub ranking layer for Phase 1.
    Future implementation should combine:
    - structured filters
    - lexical matching
    - semantic retrieval (pgvector)
    - relationship signals
    """

    return [
        Recommendation(
            person_id="person_001",
            full_name="Asha Patel",
            role="Principal Data Consultant",
            confidence_score=0.79,
            why_recommended=[
                "Strong match for requested data platform and client delivery skills.",
                "Recent project evidence in BFSI domain.",
            ],
            evidence_ids=["evidence_001", "project_001"],
            uncertainties=[
                "Availability status should be confirmed with current pod lead.",
                "Cost fit should be validated against current deal budget.",
            ],
            next_action="Ask delivery manager to confirm availability for next 4 weeks.",
            last_updated_at=datetime.now(UTC),
        )
    ]
