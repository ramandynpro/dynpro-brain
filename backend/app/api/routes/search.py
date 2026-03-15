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
    Current behavior reads from local sample JSON with optional pilot people, assignment/project, and skill-evidence JSON files.
    """
    pod_recommendation = None
    recommendations = rank_people_for_query(query)
    if query.workflow == "pod_builder":
        recommendations = []
        pod_recommendation = build_pod_for_query(query)

    sample_data = load_sample_data()
    data_sources = sample_data.people_data_sources
    assignment_data_sources = sample_data.assignment_data_sources
    skill_evidence_data_sources = sample_data.skill_evidence_data_sources

    people_source_note = (
        "People results currently use local sample data."
        if data_sources == ["sample"]
        else "People results currently use merged local sample + pilot data (pilot records override sample on matching person_id)."
    )
    assignment_source_note = (
        "Assignment/project context currently uses local sample data."
        if assignment_data_sources == ["sample"]
        else "Assignment/project context currently uses merged local sample + pilot data (pilot records override sample on matching assignment_id/project_id)."
    )
    skill_evidence_source_note = (
        "Skill-evidence context currently uses local sample data."
        if skill_evidence_data_sources == ["sample"]
        else "Skill-evidence context currently uses merged local sample + pilot data (pilot records override sample on matching evidence_id)."
    )

    response = SearchResponse(
        query=query,
        recommendations=recommendations,
        pod_recommendation=pod_recommendation,
        data_sources=data_sources,
        assignment_data_sources=assignment_data_sources,
        skill_evidence_data_sources=skill_evidence_data_sources,
        notes=[
            "Human review is required before making staffing decisions.",
            "Scores are confidence hints, not final truth.",
            people_source_note,
            assignment_source_note,
            skill_evidence_source_note,
        ],
    )
    response.request_id = log_search_request(query=query, response=response)
    return response
