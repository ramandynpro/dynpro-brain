from fastapi import APIRouter

from app.models.search import SearchQuery, SearchResponse
from app.services.pilot_tracking import log_search_request
from app.services.ranking import (
    build_pod_for_query,
    is_commercial_aware_mode,
    normalize_viewer_mode,
    rank_people_for_query,
)
from app.services.sample_data import load_sample_data

router = APIRouter(tags=["search"])

def _budget_band_from_rate(rate: float | int | None) -> str:
    if rate is None:
        return "unknown"
    value = float(rate)
    if value <= 110:
        return "economy"
    if value <= 130:
        return "standard"
    return "premium"


def _apply_commercial_masking(response: SearchResponse) -> SearchResponse:
    viewer_mode = normalize_viewer_mode(response.query.viewer_mode)
    response.viewer_mode = viewer_mode
    if is_commercial_aware_mode(viewer_mode):
        response.commercial_masking_applied = False
        response.commercial_visibility_note = "Commercial-aware mode: detailed commercial fields are visible in the UI."
        return response

    response.commercial_masking_applied = True
    response.commercial_visibility_note = (
        "Broad user mode: exact commercial fields are masked. Recommendations still use budget fit and explainability."
    )

    if response.pod_recommendation:
        for person in response.pod_recommendation.get("recommended_people", []):
            band = _budget_band_from_rate(person.get("bill_rate_usd"))
            person["bill_rate_usd"] = None
            person["budget_band"] = band
            person["commercial_masked"] = True
        budget_fit_summary = response.pod_recommendation.get("budget_fit_summary") or {}
        if "estimated_total_bill_rate" in budget_fit_summary:
            budget_fit_summary["estimated_total_bill_rate"] = None
            budget_fit_summary["estimated_total_budget_band"] = "masked_for_broad_user"
            budget_fit_summary["notes"] = (
                f"{budget_fit_summary.get('notes', '')} Exact total rate is masked in broad_user mode; use budget band guidance."
            ).strip()
            response.pod_recommendation["budget_fit_summary"] = budget_fit_summary

    return response



@router.post("/search", response_model=SearchResponse)
def search_people(query: SearchQuery) -> SearchResponse:
    """
    Phase-1 hybrid-ready search endpoint.
    Current behavior reads from local sample JSON with optional pilot people, assignment/project, skill-evidence, and commercial JSON files.
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
    commercial_data_sources = sample_data.commercial_data_sources

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

    commercial_source_note = (
        "Commercial-profile context currently uses local sample data."
        if commercial_data_sources == ["sample"]
        else "Commercial-profile context currently uses merged local sample + pilot data (pilot records override sample on matching commercial_profile_id/commercial_id)."
    )

    viewer_mode = normalize_viewer_mode(query.viewer_mode)

    response = SearchResponse(
        query=query.model_copy(update={"viewer_mode": viewer_mode}),
        recommendations=recommendations,
        pod_recommendation=pod_recommendation,
        data_sources=data_sources,
        assignment_data_sources=assignment_data_sources,
        skill_evidence_data_sources=skill_evidence_data_sources,
        commercial_data_sources=commercial_data_sources,
        notes=[
            "Human review is required before making staffing decisions.",
            "Scores are confidence hints, not final truth.",
            people_source_note,
            assignment_source_note,
            skill_evidence_source_note,
            commercial_source_note,
        ],
    )
    response = _apply_commercial_masking(response)
    response.request_id = log_search_request(query=response.query, response=response)
    return response
