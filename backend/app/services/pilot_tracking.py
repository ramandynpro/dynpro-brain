import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from app.models.pilot import (
    PilotDurationSummary,
    PilotFeedbackCreate,
    PilotFeedbackRecord,
    PilotFeedbackSummary,
    PilotKpiSummary,
    PilotRecentResponse,
    PilotRequestLog,
)
from app.models.search import SearchQuery, SearchResponse

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
