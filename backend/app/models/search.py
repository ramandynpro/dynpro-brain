from datetime import date, datetime

from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    workflow: str = Field(
        default="expert_finder",
        description="Phase 1 workflow identifier such as expert_finder.",
    )
    text_query: str = Field(..., description="Plain language request from user.")
    skill_filters: list[str] = Field(default_factory=list)
    domain_filters: list[str] = Field(default_factory=list)
    internal_external: str | None = None
    country: str | None = None
    location: str | None = None
    timezone: str | None = None
    practice: str | None = None
    minimum_available_percent: int | None = Field(default=None, ge=0, le=100)
    available_by_date: date | None = None
    max_bill_rate: float | None = Field(default=None, gt=0)
    budget_band: str | None = None


class Recommendation(BaseModel):
    person_id: str
    full_name: str
    role: str
    confidence_score: float = Field(ge=0, le=1)
    why_recommended: list[str]
    evidence_ids: list[str]
    uncertainties: list[str]
    next_action: str
    last_updated_at: datetime


class SearchResponse(BaseModel):
    query: SearchQuery
    recommendations: list[Recommendation]
    notes: list[str]
