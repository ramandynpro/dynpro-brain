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
    client_name: str | None = None
    domain_name: str | None = None
    minimum_available_percent: int | None = Field(default=None, ge=0, le=100)
    available_by_date: date | None = None
    max_bill_rate: float | None = Field(default=None, gt=0)
    budget_band: str | None = None
    interviewer_only: bool = False
    minimum_prior_interview_count: int | None = Field(default=None, ge=0)
    poc_support_only: bool = False
    minimum_client_facing_comfort: str | None = None
    minimum_poc_participation_count: int | None = Field(default=None, ge=0)
    required_skills: list[str] = Field(default_factory=list)
    desired_roles: list[str] = Field(default_factory=list)
    pod_size: int | None = Field(default=None, ge=1, le=10)
    internal_external_preference: str | None = None
    budget_ceiling: float | None = Field(default=None, gt=0)
    worked_with_person_id: str | None = None
    worked_with_person_name: str | None = None
    prefer_people_who_worked_together: bool = False


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
    pod_recommendation: dict | None = None
    notes: list[str]
