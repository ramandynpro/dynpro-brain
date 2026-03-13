from fastapi import APIRouter

from app.models.search import SearchQuery, SearchResponse
from app.services.ranking import rank_people_for_query

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
def search_people(query: SearchQuery) -> SearchResponse:
    """
    MVP placeholder for hybrid retrieval.
    Current behavior returns scaffolded explainability-ready records.
    """
    recommendations = rank_people_for_query(query)
    return SearchResponse(
        query=query,
        recommendations=recommendations,
        notes=[
            "Human review is required before making staffing decisions.",
            "Scores are confidence hints, not final truth.",
        ],
    )
