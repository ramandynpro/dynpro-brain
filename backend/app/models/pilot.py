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
    field_name: str
    sample_count: int = Field(ge=0)
    average_ms: float = Field(ge=0)
    min_ms: float = Field(ge=0)
    max_ms: float = Field(ge=0)


class PilotKpiSummary(BaseModel):
    total_requests: int = Field(ge=0)
    requests_by_workflow: dict[str, int] = Field(default_factory=dict)
    average_trust_rating: float | None = None
    useful_yes_rate: float | None = None
    recent_missed_person_or_gap_count: int = Field(ge=0)
    pod_builder_request_count: int = Field(ge=0)
    interviewer_finder_request_count: int = Field(ge=0)
    duration_summary: PilotDurationSummary | None = None


class PilotAdminResponse(BaseModel):
    kpi_summary: PilotKpiSummary
    recent_requests: list[PilotRequestLog]
    recent_feedback: list[PilotFeedbackRecord]
