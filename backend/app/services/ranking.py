from datetime import date, datetime, timezone

from app.models.search import Recommendation, SearchQuery
from app.services.sample_data import load_sample_data


BUDGET_BAND_LIMITS = {
    "economy": 110.0,
    "standard": 130.0,
    "premium": 160.0,
}


def _contains_any(haystack: str, needles: list[str]) -> bool:
    if not needles:
        return True
    haystack_lower = haystack.lower()
    return any(needle.lower() in haystack_lower for needle in needles)


def _matches_filter(value: str | None, requested: str | None) -> bool:
    if not requested:
        return True
    return str(value or "").strip().lower() == requested.strip().lower()


def _country_from_location(location: str | None) -> str:
    if not location:
        return ""
    parts = [part.strip() for part in location.split(",") if part.strip()]
    return parts[-1] if parts else ""


def _parse_last_updated(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _availability_rank_boost(availability_percent: int, effective_from: date | None) -> float:
    percent_boost = min(max(availability_percent, 0), 100) / 1000
    if not effective_from:
        return percent_boost

    days_until_available = (effective_from - datetime.now(timezone.utc).date()).days
    if days_until_available <= 0:
        return percent_boost + 0.03
    if days_until_available <= 30:
        return percent_boost + 0.015
    return percent_boost


def _budget_band_limit(budget_band: str | None) -> float | None:
    if not budget_band:
        return None
    return BUDGET_BAND_LIMITS.get(budget_band.strip().lower())


def _budget_fit_rank_boost(bill_rate: float | None, max_bill_rate: float | None) -> float:
    if bill_rate is None or max_bill_rate is None or max_bill_rate <= 0:
        return 0.0

    utilization = bill_rate / max_bill_rate
    if utilization <= 0.8:
        return 0.03
    if utilization <= 0.95:
        return 0.015
    if utilization <= 1:
        return 0.005
    return 0.0


def rank_people_for_query(query: SearchQuery) -> list[Recommendation]:
    """
    Simple phase-1 ranking using sample JSON data.
    Uses lightweight lexical matching and explainability fields.
    """

    data = load_sample_data()
    recommendations: list[Recommendation] = []

    for person in data.people:
        person_id = person.get("person_id", "")
        evidence = [
            item
            for item in data.skill_evidence
            if item.get("person_id") == person_id
            and query.workflow in item.get("metadata", {}).get("workflow_tags", [])
        ]
        assignments = [item for item in data.assignments if item.get("person_id") == person_id]
        commercial = next(
            (item for item in data.commercial_profiles if item.get("person_id") == person_id),
            None,
        )

        person_timezone = str(person.get("timezone", ""))
        person_country = _country_from_location(str(person.get("home_location", "")))
        internal_external = str(person.get("internal_external", "internal"))
        practice = str(person.get("practice", "Unknown"))

        if not _matches_filter(internal_external, query.internal_external):
            continue
        if not _matches_filter(person_country, query.country):
            continue
        if not _matches_filter(person_timezone, query.timezone):
            continue
        if not _matches_filter(practice, query.practice):
            continue

        availability_percent = int((commercial or {}).get("availability_percent", 0))
        available_from_date = _parse_iso_date((commercial or {}).get("effective_from"))
        bill_rate = float((commercial or {}).get("bill_rate_usd", 0)) if commercial else None

        budget_limit = query.max_bill_rate
        band_limit = _budget_band_limit(query.budget_band)
        if budget_limit is None and band_limit is not None:
            budget_limit = band_limit
        elif budget_limit is not None and band_limit is not None:
            budget_limit = min(budget_limit, band_limit)

        if budget_limit is not None and (bill_rate is None or bill_rate > budget_limit):
            continue

        if (
            query.minimum_available_percent is not None
            and availability_percent < query.minimum_available_percent
        ):
            continue
        if query.available_by_date and (
            not available_from_date or available_from_date > query.available_by_date
        ):
            continue

        combined_text = " ".join(
            [
                str(person.get("summary", "")),
                " ".join(str(item.get("skill_name", "")) for item in evidence),
                " ".join(str(item.get("domain", "")) for item in assignments),
                " ".join(str(item.get("project_summary", "")) for item in assignments),
            ]
        )

        if not _contains_any(combined_text, query.skill_filters):
            continue
        if not _contains_any(combined_text, query.domain_filters):
            continue

        confidence_parts = [float(person.get("profile_confidence", 0.5))]
        confidence_parts.extend(float(item.get("confidence", 0.5)) for item in evidence)
        confidence_parts.extend(float(item.get("confidence", 0.5)) for item in assignments)
        if commercial:
            confidence_parts.append(float(commercial.get("confidence", 0.5)))

        confidence = round(sum(confidence_parts) / max(len(confidence_parts), 1), 2)
        availability_boost = _availability_rank_boost(availability_percent, available_from_date)
        budget_boost = _budget_fit_rank_boost(bill_rate, budget_limit)
        confidence = round(min(1.0, confidence + availability_boost + budget_boost), 2)

        why_recommended = [
            "Profile summary and project history match the current request context.",
        ]
        if evidence:
            why_recommended.append(
                f"Matched {len(evidence)} skill evidence record(s) for workflow {query.workflow}."
            )
        if assignments:
            domains = ", ".join(sorted({a.get("domain", "unknown") for a in assignments}))
            why_recommended.append(
                f"Recent assignment evidence found in domains: {domains}."
            )
        if availability_percent > 0 or available_from_date:
            availability_detail = f"{availability_percent}% availability"
            if available_from_date:
                availability_detail += f" from {available_from_date.isoformat()}"
            why_recommended.append(
                f"Availability influenced ranking with a small boost ({availability_detail})."
            )
        if budget_boost > 0 and budget_limit is not None:
            why_recommended.append(
                "Budget fit influenced ranking with a small boost (good fit to selected budget constraints)."
            )

        uncertainties = [
            "Validate latest availability with delivery lead before staffing.",
        ]
        if commercial and commercial.get("availability_note"):
            uncertainties.append(str(commercial["availability_note"]))

        recommendations.append(
            Recommendation(
                person_id=person_id,
                full_name=str(person.get("full_name", "Unknown")),
                role=str(person.get("current_role", "Unknown role")),
                confidence_score=confidence,
                why_recommended=why_recommended,
                evidence_ids=[
                    str(item.get("evidence_id"))
                    for item in evidence
                    if item.get("evidence_id")
                ]
                + [
                    str(item.get("project_id"))
                    for item in assignments
                    if item.get("project_id")
                ],
                uncertainties=uncertainties,
                next_action="Review evidence and confirm availability before recommending to client.",
                last_updated_at=_parse_last_updated(
                    str(person.get("profile_last_updated_at", ""))
                ),
            )
        )

    return sorted(recommendations, key=lambda item: item.confidence_score, reverse=True)
