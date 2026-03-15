from fastapi import APIRouter

from app.models.search import SearchQuery, SearchResponse
from app.services.pilot_tracking import log_search_request
from app.services.ranking import build_pod_for_query, rank_people_for_query

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
def search_people(query: SearchQuery) -> SearchResponse:
    """
    Phase-1 hybrid-ready search endpoint.
    Current behavior reads from local sample JSON via the ranking service.
    """
    pod_recommendation = None
    recommendations = rank_people_for_query(query)
    if query.workflow == "pod_builder":
        recommendations = []
        pod_recommendation = build_pod_for_query(query)

    response = SearchResponse(
        query=query,
        recommendations=recommendations,
        pod_recommendation=pod_recommendation,
        notes=[
            "Human review is required before making staffing decisions.",
            "Scores are confidence hints, not final truth.",
            "Results currently come from local sample JSON while DB ingestion is being wired.",
        ],
    )
    response.request_id = log_search_request(query=query, response=response)
    return response
