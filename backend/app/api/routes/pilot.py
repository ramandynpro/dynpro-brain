from fastapi import APIRouter, Query

from app.models.pilot import (
    PilotAdminResponse,
    PilotFeedbackCreate,
    PilotFeedbackRecord,
    PilotRecentResponse,
)
from app.services.pilot_tracking import (
    get_pilot_kpi_summary,
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


@router.get("/kpi", response_model=PilotAdminResponse)
def get_pilot_kpis(limit: int = Query(default=20, ge=1, le=100)) -> PilotAdminResponse:
    return get_pilot_kpi_summary(recent_limit=limit)
