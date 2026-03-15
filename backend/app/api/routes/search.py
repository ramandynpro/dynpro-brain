from fastapi import APIRouter

from app.models.search import SearchQuery, SearchResponse
from app.services.pilot_tracking import log_search_request
from app.services.ranking import build_pod_for_query, rank_people_for_query
from app.services.sample_data import load_sample_data

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
def search_people(query: SearchQuery) -> SearchResponse:
    """
    Phase-1 hybrid-ready search endpoint.
    Current behavior reads from local sample JSON and optional pilot people JSON.
    """
    pod_recommendation = None
    recommendations = rank_people_for_query(query)
    if query.workflow == "pod_builder":
        recommendations = []
        pod_recommendation = build_pod_for_query(query)

    data_sources = load_sample_data().people_data_sources
    source_note = (
        "Results currently use local sample people data."
        if data_sources == ["sample"]
        else "Results currently use merged local sample + pilot people data (pilot records override sample on matching person_id)."
    )

    response = SearchResponse(
        query=query,
        recommendations=recommendations,
        pod_recommendation=pod_recommendation,
        data_sources=data_sources,
        notes=[
            "Human review is required before making staffing decisions.",
            "Scores are confidence hints, not final truth.",
            source_note,
        ],
    )
    response.request_id = log_search_request(query=query, response=response)
    return response
