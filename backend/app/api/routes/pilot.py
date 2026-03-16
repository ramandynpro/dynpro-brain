from fastapi import APIRouter, Query

from app.models.pilot import (
    PilotDataQualitySummary,
    PilotFeedbackCreate,
    PilotFeedbackRecord,
    PilotKpiSummary,
    PilotRecentResponse,
)
from app.services.pilot_tracking import (
    get_data_quality_summary,
    get_kpi_summary,
    get_recent_requests_with_feedback,
    submit_feedback,
)

router = APIRouter(prefix="/pilot", tags=["pilot"])


@router.post("/feedback", response_model=PilotFeedbackRecord)
def create_feedback(feedback: PilotFeedbackCreate) -> PilotFeedbackRecord:
    return submit_feedback(feedback)


@router.get("/recent", response_model=PilotRecentResponse)
def list_recent_pilot_activity(limit: int = Query(default=20, ge=1, le=100)) -> PilotRecentResponse:
    return get_recent_requests_with_feedback(limit=limit)


@router.get("/kpi-summary", response_model=PilotKpiSummary)
def get_pilot_kpi_summary(limit: int = Query(default=20, ge=1, le=100)) -> PilotKpiSummary:
    return get_kpi_summary(limit=limit)


@router.get("/data-quality", response_model=PilotDataQualitySummary)
def get_pilot_data_quality_summary(
    stale_profile_days: int = Query(default=90, ge=1, le=3650),
    low_confidence_threshold: float = Query(default=0.6, ge=0.0, le=1.0),
    example_limit: int = Query(default=10, ge=1, le=50),
) -> PilotDataQualitySummary:
    return get_data_quality_summary(
        stale_profile_days=stale_profile_days,
        low_confidence_threshold=low_confidence_threshold,
        example_limit=example_limit,
    )
