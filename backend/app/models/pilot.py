from datetime import datetime

from pydantic import BaseModel, Field


class PilotRequestLog(BaseModel):
    request_id: str
    timestamp: datetime
    workflow: str
    input_summary: str
    result_count: int = Field(ge=0)
    top_result_ids: list[str] = Field(default_factory=list)
    confidence_summary: str | None = None


class PilotFeedbackCreate(BaseModel):
    request_id: str
    useful_yes_no: bool
    trust_rating: int = Field(ge=1, le=5)
    notes: str | None = None
    missed_person_or_gap: str | None = None


class PilotFeedbackRecord(PilotFeedbackCreate):
    timestamp: datetime


class PilotFeedbackSummary(BaseModel):
    request_id: str
    feedback_count: int = Field(ge=0)
    useful_yes_count: int = Field(ge=0)
    average_trust_rating: float | None = None


class PilotRecentResponse(BaseModel):
    requests: list[PilotRequestLog]
    feedback_summaries: list[PilotFeedbackSummary]


class PilotDurationSummary(BaseModel):
    metric_name: str
    average: float
    minimum: float
    maximum: float


class PilotKpiSummary(BaseModel):
    total_requests: int = Field(ge=0)
    requests_by_workflow: dict[str, int] = Field(default_factory=dict)
    average_trust_rating: float | None = None
    useful_yes_rate: float | None = None
    recent_missed_person_or_gap_count: int = Field(ge=0)
    pod_builder_request_count: int = Field(ge=0)
    interviewer_finder_request_count: int = Field(ge=0)
    duration_summary: PilotDurationSummary | None = None
    recent_requests: list[PilotRequestLog] = Field(default_factory=list)
    recent_feedback: list[PilotFeedbackRecord] = Field(default_factory=list)
