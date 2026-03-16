import json
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.models.pilot import (
    PilotDurationSummary,
    PilotFeedbackCreate,
    PilotFeedbackRecord,
    DataQualityCoverageSummary,
    DataQualityIssueExample,
    PilotDataQualitySummary,
    PilotFeedbackSummary,
    PilotKpiSummary,
    PilotRecentResponse,
    PilotRequestLog,
)
from app.models.search import SearchQuery, SearchResponse
from app.services.sample_data import load_sample_data

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
REQUEST_LOG_PATH = DATA_DIR / "pilot_request_log.jsonl"
FEEDBACK_LOG_PATH = DATA_DIR / "pilot_feedback_log.jsonl"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _append_jsonl(path: Path, payload: dict) -> None:
    _ensure_data_dir()
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=True) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []

    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _build_input_summary(query: SearchQuery) -> str:
    summary_parts = [query.text_query.strip()]

    if query.skill_filters:
        summary_parts.append(f"skills={', '.join(query.skill_filters)}")
    if query.domain_filters:
        summary_parts.append(f"domains={', '.join(query.domain_filters)}")
    if query.client_name:
        summary_parts.append(f"client={query.client_name}")
    if query.domain_name:
        summary_parts.append(f"domain={query.domain_name}")

    return " | ".join(part for part in summary_parts if part)


def _build_confidence_summary(response: SearchResponse) -> str | None:
    if response.recommendations:
        bands = [rec.confidence_band for rec in response.recommendations]
        high_count = sum(1 for band in bands if band == "high")
        medium_count = sum(1 for band in bands if band == "medium")
        low_count = sum(1 for band in bands if band == "low")
        return f"high={high_count}, medium={medium_count}, low={low_count}"

    if response.pod_recommendation:
        uncertainties = response.pod_recommendation.get("uncertainties") or []
        if uncertainties:
            return f"Pod uncertainties noted: {len(uncertainties)}"
        return "Pod generated with no explicit uncertainties listed."

    return None


def _extract_duration_minutes_from_notes(notes: str | None) -> float | None:
    if not notes:
        return None

    lowered = notes.lower()
    marker = "duration_minutes="
    if marker not in lowered:
        return None

    try:
        trailing = lowered.split(marker, maxsplit=1)[1].strip()
        value_part = trailing.split()[0]
        return float(value_part)
    except (ValueError, IndexError):
        return None


def log_search_request(query: SearchQuery, response: SearchResponse) -> str:
    request_id = uuid.uuid4().hex[:12]
    top_result_ids: list[str] = []

    if response.recommendations:
        top_result_ids = [rec.person_id for rec in response.recommendations[:5]]
    elif response.pod_recommendation:
        recommended_people = response.pod_recommendation.get("recommended_people") or []
        top_result_ids = [person.get("person_id") for person in recommended_people[:5] if person.get("person_id")]

    request_log = PilotRequestLog(
        request_id=request_id,
        timestamp=datetime.now(timezone.utc),
        workflow=query.workflow,
        input_summary=_build_input_summary(query),
        result_count=len(top_result_ids),
        top_result_ids=top_result_ids,
        confidence_summary=_build_confidence_summary(response),
    )

    _append_jsonl(REQUEST_LOG_PATH, request_log.model_dump(mode="json"))
    return request_id


def submit_feedback(feedback: PilotFeedbackCreate) -> PilotFeedbackRecord:
    feedback_record = PilotFeedbackRecord(
        timestamp=datetime.now(timezone.utc),
        **feedback.model_dump(),
    )
    _append_jsonl(FEEDBACK_LOG_PATH, feedback_record.model_dump(mode="json"))
    return feedback_record


def get_recent_requests_with_feedback(limit: int = 20) -> PilotRecentResponse:
    request_rows = _read_jsonl(REQUEST_LOG_PATH)
    feedback_rows = _read_jsonl(FEEDBACK_LOG_PATH)

    recent_request_rows = request_rows[-limit:]
    requests = [PilotRequestLog.model_validate(row) for row in recent_request_rows]

    grouped_feedback: dict[str, list[PilotFeedbackRecord]] = defaultdict(list)
    for row in feedback_rows:
        record = PilotFeedbackRecord.model_validate(row)
        grouped_feedback[record.request_id].append(record)

    feedback_summaries: list[PilotFeedbackSummary] = []
    for request in requests:
        records = grouped_feedback.get(request.request_id, [])
        if not records:
            continue
        useful_yes_count = sum(1 for record in records if record.useful_yes_no)
        average_trust_rating = sum(record.trust_rating for record in records) / len(records)
        feedback_summaries.append(
            PilotFeedbackSummary(
                request_id=request.request_id,
                feedback_count=len(records),
                useful_yes_count=useful_yes_count,
                average_trust_rating=round(average_trust_rating, 2),
            )
        )

    return PilotRecentResponse(requests=requests, feedback_summaries=feedback_summaries)


def get_kpi_summary(limit: int = 20) -> PilotKpiSummary:
    request_records = [PilotRequestLog.model_validate(row) for row in _read_jsonl(REQUEST_LOG_PATH)]
    feedback_records = [PilotFeedbackRecord.model_validate(row) for row in _read_jsonl(FEEDBACK_LOG_PATH)]

    requests_by_workflow: dict[str, int] = defaultdict(int)
    for record in request_records:
        requests_by_workflow[record.workflow] += 1

    average_trust_rating = None
    useful_yes_rate = None
    if feedback_records:
        average_trust_rating = round(
            sum(record.trust_rating for record in feedback_records) / len(feedback_records), 2
        )
        useful_yes_rate = round(
            sum(1 for record in feedback_records if record.useful_yes_no) / len(feedback_records), 3
        )

    recent_feedback = feedback_records[-limit:]
    recent_missed_person_or_gap_count = sum(
        1 for record in recent_feedback if (record.missed_person_or_gap or "").strip()
    )

    duration_values = [
        value
        for value in (
            _extract_duration_minutes_from_notes(record.notes)
            for record in feedback_records
        )
        if value is not None
    ]

    duration_summary = None
    if duration_values:
        duration_summary = PilotDurationSummary(
            metric_name="duration_minutes",
            average=round(sum(duration_values) / len(duration_values), 2),
            minimum=round(min(duration_values), 2),
            maximum=round(max(duration_values), 2),
        )

    return PilotKpiSummary(
        total_requests=len(request_records),
        requests_by_workflow=dict(requests_by_workflow),
        average_trust_rating=average_trust_rating,
        useful_yes_rate=useful_yes_rate,
        recent_missed_person_or_gap_count=recent_missed_person_or_gap_count,
        pod_builder_request_count=requests_by_workflow.get("pod_builder", 0),
        interviewer_finder_request_count=requests_by_workflow.get("interviewer_finder", 0),
        duration_summary=duration_summary,
        recent_requests=request_records[-limit:],
        recent_feedback=recent_feedback,
    )


def _as_non_empty_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _parse_iso_datetime(value: object) -> datetime | None:
    text_value = _as_non_empty_text(value)
    if not text_value:
        return None
    try:
        normalized = text_value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def get_data_quality_summary(
    stale_profile_days: int = 90,
    low_confidence_threshold: float = 0.6,
    example_limit: int = 10,
) -> PilotDataQualitySummary:
    sample_data = load_sample_data()
    people = sample_data.people
    commercial_profiles = sample_data.commercial_profiles

    commercial_profiles_by_person_id: dict[str, dict] = {}
    for profile in commercial_profiles:
        profile_person_id = _as_non_empty_text(profile.get("person_id"))
        if profile_person_id and profile_person_id not in commercial_profiles_by_person_id:
            commercial_profiles_by_person_id[profile_person_id] = profile

    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(days=stale_profile_days)

    missing_required_profile_field_count = 0
    missing_timezone_count = 0
    missing_country_count = 0
    missing_practice_count = 0
    missing_availability_field_count = 0
    missing_commercial_field_count = 0
    low_confidence_profile_count = 0
    stale_profile_count = 0

    examples: list[DataQualityIssueExample] = []

    for person in people:
        issues: list[str] = []
        person_id = _as_non_empty_text(person.get("person_id")) or "unknown_person"

        required_fields = ["person_id", "full_name", "current_role", "profile_last_updated_at"]
        missing_required = [field for field in required_fields if not _as_non_empty_text(person.get(field))]
        if missing_required:
            missing_required_profile_field_count += 1
            issues.append(f"Missing required profile fields: {', '.join(missing_required)}")

        timezone_value = _as_non_empty_text(person.get("timezone"))
        if not timezone_value:
            missing_timezone_count += 1
            issues.append("Missing timezone")

        home_location_value = _as_non_empty_text(person.get("home_location")).lower()
        if not home_location_value:
            missing_country_count += 1
            issues.append("Missing country/home_location")

        practice_value = _as_non_empty_text(person.get("practice"))
        if not practice_value:
            missing_practice_count += 1
            issues.append("Missing practice")

        # Availability and commercial fields are sourced from linked commercial profiles.
        linked_commercial_profile = commercial_profiles_by_person_id.get(person_id)

        availability_percent = None
        available_by_date = ""
        if linked_commercial_profile:
            availability_percent = linked_commercial_profile.get("availability_percent")
            available_by_date = _as_non_empty_text(linked_commercial_profile.get("available_by_date"))
        if availability_percent is None and not available_by_date:
            missing_availability_field_count += 1
            issues.append("Missing availability fields (availability_percent and available_by_date)")

        bill_rate = None
        budget_band = ""
        if linked_commercial_profile:
            bill_rate = linked_commercial_profile.get("bill_rate_usd")
            budget_band = _as_non_empty_text(linked_commercial_profile.get("budget_band"))
        if bill_rate is None and not budget_band:
            missing_commercial_field_count += 1
            issues.append("Missing commercial fields (bill_rate_usd and budget_band)")

        profile_confidence = person.get("profile_confidence")
        confidence_value = None
        if isinstance(profile_confidence, (float, int)):
            confidence_value = float(profile_confidence)
        else:
            text_profile_confidence = _as_non_empty_text(profile_confidence)
            if text_profile_confidence:
                try:
                    confidence_value = float(text_profile_confidence)
                except ValueError:
                    confidence_value = None

        if confidence_value is not None and confidence_value < low_confidence_threshold:
            low_confidence_profile_count += 1
            issues.append(f"Low profile confidence ({round(confidence_value, 2)})")

        last_verified_at = _parse_iso_datetime(person.get("last_verified_at"))
        if not last_verified_at or last_verified_at < stale_cutoff:
            stale_profile_count += 1
            if not last_verified_at:
                issues.append("Stale profile: last_verified_at missing")
            else:
                issues.append("Stale profile: last_verified_at older than threshold")

        if issues and len(examples) < example_limit:
            examples.append(DataQualityIssueExample(record_type="person", record_id=person_id, issues=issues))

    person_ids = {
        _as_non_empty_text(person.get("person_id"))
        for person in people
        if _as_non_empty_text(person.get("person_id"))
    }

    assignments = sample_data.assignments
    skill_evidence = sample_data.skill_evidence
    relationship_edges = sample_data.relationship_edges
    assignments_missing_person_link = sum(
        1
        for assignment in assignments
        if _as_non_empty_text(assignment.get("person_id")) not in person_ids
    )
    skill_evidence_missing_person_link = sum(
        1
        for evidence in skill_evidence
        if _as_non_empty_text(evidence.get("person_id")) not in person_ids
    )
    relationship_edges_missing_person_link = sum(
        1
        for edge in relationship_edges
        if _as_non_empty_text(edge.get("from_person_id")) not in person_ids
        or _as_non_empty_text(edge.get("to_person_id")) not in person_ids
    )
    commercial_profiles_missing_person_link = sum(
        1
        for profile in commercial_profiles
        if _as_non_empty_text(profile.get("person_id")) not in person_ids
    )

    return PilotDataQualitySummary(
        people_loaded=len(people),
        low_confidence_profile_count=low_confidence_profile_count,
        stale_profile_count=stale_profile_count,
        missing_required_profile_field_count=missing_required_profile_field_count,
        missing_timezone_count=missing_timezone_count,
        missing_country_count=missing_country_count,
        missing_practice_count=missing_practice_count,
        missing_availability_field_count=missing_availability_field_count,
        missing_commercial_field_count=missing_commercial_field_count,
        low_confidence_threshold=low_confidence_threshold,
        stale_profile_days=stale_profile_days,
        people_data_sources=sample_data.people_data_sources,
        assignment_data_sources=sample_data.assignment_data_sources,
        skill_evidence_data_sources=sample_data.skill_evidence_data_sources,
        commercial_data_sources=sample_data.commercial_data_sources,
        coverage=DataQualityCoverageSummary(
            assignments_loaded=len(assignments),
            assignments_missing_person_link=assignments_missing_person_link,
            skill_evidence_loaded=len(skill_evidence),
            skill_evidence_missing_person_link=skill_evidence_missing_person_link,
            relationship_edges_loaded=len(relationship_edges),
            relationship_edges_missing_person_link=relationship_edges_missing_person_link,
            commercial_profiles_loaded=len(commercial_profiles),
            commercial_profiles_missing_person_link=commercial_profiles_missing_person_link,
        ),
        example_problematic_records=examples,
    )
