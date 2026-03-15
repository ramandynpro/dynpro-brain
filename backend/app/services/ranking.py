from datetime import date, datetime, timezone

from app.models.search import Recommendation, SearchQuery
from app.services.sample_data import load_sample_data


BUDGET_BAND_LIMITS = {
    "economy": 110.0,
    "standard": 130.0,
    "premium": 160.0,
}


CLIENT_FACING_COMFORT_LEVELS = {
    "low": 1,
    "medium": 2,
    "high": 3,
}


def _client_facing_comfort_level(value: str | None) -> int:
    return CLIENT_FACING_COMFORT_LEVELS.get(str(value or "").strip().lower(), 0)


def _contains_any(haystack: str, needles: list[str]) -> bool:
    if not needles:
        return True
    haystack_lower = haystack.lower()
    return any(needle.lower() in haystack_lower for needle in needles)


def _matches_filter(value: str | None, requested: str | None) -> bool:
    if not requested:
        return True
    return str(value or "").strip().lower() == requested.strip().lower()


def _matches_requested_name(value: str | None, requested: str | None) -> bool:
    if not requested:
        return True
    return requested.strip().lower() in str(value or "").strip().lower()


def _normalized_values(values: list[str] | None) -> set[str]:
    return {str(value).strip().lower() for value in values or [] if str(value).strip()}


def _normalized_text(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _client_domain_rank_boost(
    assignments: list[dict],
    top_clients: list[str] | None,
    top_domains: list[str] | None,
    client_name: str | None,
    domain_name: str | None,
) -> tuple[float, list[str]]:
    boost = 0.0
    reasons: list[str] = []

    requested_client = (client_name or "").strip().lower()
    requested_domain = (domain_name or "").strip().lower()

    assignment_clients = {
        str(item.get("client_name", "")).strip().lower()
        for item in assignments
        if str(item.get("client_name", "")).strip()
    }
    assignment_domains = {
        str(item.get("domain", "")).strip().lower()
        for item in assignments
        if str(item.get("domain", "")).strip()
    }
    top_client_values = _normalized_values(top_clients)
    top_domain_values = _normalized_values(top_domains)

    if requested_client and (requested_client in assignment_clients or requested_client in top_client_values):
        boost += 0.02
        reasons.append(f"client match: {client_name}")
    if requested_domain and (requested_domain in assignment_domains or requested_domain in top_domain_values):
        boost += 0.02
        reasons.append(f"domain match: {domain_name}")

    return boost, reasons




def _build_relationship_lookup(relationship_edges: list[dict]) -> dict[str, list[dict[str, str | float]]]:
    relationship_lookup: dict[str, list[dict[str, str | float]]] = {}

    for edge in relationship_edges:
        relationship_type = str(edge.get("relationship_type", "")).strip().lower()
        if relationship_type != "worked_with":
            continue

        from_person_id = str(edge.get("from_person_id", "")).strip()
        to_person_id = str(edge.get("to_person_id", "")).strip()
        if not from_person_id or not to_person_id:
            continue

        strength = float(edge.get("strength", 0.0) or 0.0)
        context_note = str(edge.get("context_note", "")).strip()

        relationship_lookup.setdefault(from_person_id, []).append(
            {
                "person_id": to_person_id,
                "strength": strength,
                "context_note": context_note,
            }
        )
        relationship_lookup.setdefault(to_person_id, []).append(
            {
                "person_id": from_person_id,
                "strength": strength,
                "context_note": context_note,
            }
        )

    return relationship_lookup


def _resolve_person_id_by_name(people: list[dict], requested_name: str | None) -> str | None:
    if not requested_name:
        return None

    requested_name_normalized = requested_name.strip().lower()
    if not requested_name_normalized:
        return None

    for person in people:
        full_name = str(person.get("full_name", "")).strip().lower()
        if requested_name_normalized == full_name:
            return str(person.get("person_id", "")).strip() or None

    for person in people:
        full_name = str(person.get("full_name", "")).strip().lower()
        if requested_name_normalized in full_name:
            return str(person.get("person_id", "")).strip() or None

    return None


def _relationship_rank_boost(
    person_id: str,
    relationship_lookup: dict[str, list[dict[str, str | float]]],
    target_person_id: str | None,
) -> tuple[float, str | None]:
    if not target_person_id:
        return 0.0, None

    matching_edges = [
        edge for edge in relationship_lookup.get(person_id, []) if edge.get("person_id") == target_person_id
    ]
    if not matching_edges:
        return 0.0, None

    strongest_edge = max(matching_edges, key=lambda edge: float(edge.get("strength", 0.0) or 0.0))
    strength = min(max(float(strongest_edge.get("strength", 0.0) or 0.0), 0.0), 1.0)
    boost = 0.01 + (strength * 0.02)
    context_note = str(strongest_edge.get("context_note", "")).strip()

    return boost, context_note or None


def _pair_relationship_boost(
    candidate_person_id: str,
    selected_people: list[dict],
    relationship_lookup: dict[str, list[dict[str, str | float]]],
) -> tuple[float, int]:
    if not selected_people:
        return 0.0, 0

    connected_edges = 0
    total_boost = 0.0

    connected_ids = {str(edge.get("person_id", "")) for edge in relationship_lookup.get(candidate_person_id, [])}
    for selected_person in selected_people:
        selected_person_id = selected_person["person_id"]
        if selected_person_id not in connected_ids:
            continue

        connected_edges += 1
        matching_edge = next(
            (
                edge
                for edge in relationship_lookup.get(candidate_person_id, [])
                if str(edge.get("person_id", "")) == selected_person_id
            ),
            None,
        )
        strength = float((matching_edge or {}).get("strength", 0.0) or 0.0)
        total_boost += 0.01 + min(max(strength, 0.0), 1.0) * 0.01

    return total_boost, connected_edges

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


def _days_old_from_iso_date(value: str | None) -> int | None:
    parsed_date = _parse_iso_date(value)
    if not parsed_date:
        return None
    return max((datetime.now(timezone.utc).date() - parsed_date).days, 0)


def _freshness_label(days_old: int) -> str:
    if days_old <= 90:
        return "fresh"
    if days_old <= 180:
        return "aging"
    return "stale"


def _confidence_band(confidence_score: float) -> str:
    if confidence_score >= 0.75:
        return "high"
    if confidence_score >= 0.5:
        return "medium"
    return "low"


def _build_confidence_layer(
    person: dict,
    evidence: list[dict],
    assignments: list[dict],
) -> tuple[float, str, str, int]:
    evidence_count = len(evidence)
    if evidence_count == 0:
        freshness_summary = "No workflow-tagged evidence yet."
        freshness_score = 0.35
    else:
        evidence_ages = [
            _days_old_from_iso_date(str(item.get("observed_at", "")))
            for item in evidence
        ]
        valid_ages = [age for age in evidence_ages if age is not None]
        if valid_ages:
            average_days = int(sum(valid_ages) / len(valid_ages))
            label = _freshness_label(average_days)
            freshness_summary = (
                f"{label.title()} evidence (avg age ~{average_days} days across {len(valid_ages)} record(s))."
            )
            freshness_score = max(0.2, 1 - (average_days / 365))
        else:
            freshness_summary = "Evidence dates missing; freshness cannot be fully verified."
            freshness_score = 0.45

    evidence_confidences = [float(item.get("confidence", 0.5)) for item in evidence]
    assignment_confidences = [float(item.get("confidence", 0.5)) for item in assignments]
    profile_confidence = float(person.get("profile_confidence", 0.5))
    profile_verified = bool(person.get("last_verified_at"))

    average_evidence_confidence = (
        sum(evidence_confidences) / len(evidence_confidences) if evidence_confidences else 0.5
    )
    average_assignment_confidence = (
        sum(assignment_confidences) / len(assignment_confidences) if assignment_confidences else 0.5
    )
    evidence_count_score = min(1.0, evidence_count / 5)
    metadata_score = 1.0 if profile_verified else 0.6

    confidence_score = round(
        (
            (evidence_count_score * 0.2)
            + (average_evidence_confidence * 0.3)
            + (average_assignment_confidence * 0.1)
            + (freshness_score * 0.25)
            + (metadata_score * 0.1)
            + (profile_confidence * 0.05)
        ),
        2,
    )
    confidence_band = _confidence_band(confidence_score)
    return confidence_score, confidence_band, freshness_summary, evidence_count


def _build_source_mix(person: dict, evidence: list[dict], assignments: list[dict], commercial: dict | None) -> dict[str, int]:
    source_mix: dict[str, int] = {}

    def _add_source(source_type: str | None) -> None:
        key = str(source_type or "unknown").strip().lower() or "unknown"
        source_mix[key] = source_mix.get(key, 0) + 1

    _add_source((person.get("source_provenance") or {}).get("source_type"))
    for item in evidence:
        _add_source((item.get("metadata") or {}).get("validated_by") or "skill_evidence")
    for item in assignments:
        _add_source((item.get("source_provenance") or {}).get("source_type"))
    if commercial:
        _add_source((commercial.get("source_provenance") or {}).get("source_type"))

    return source_mix


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


def _effective_budget_limit(query: SearchQuery) -> float | None:
    budget_limit = query.max_bill_rate
    band_limit = _budget_band_limit(query.budget_band)
    if budget_limit is None and band_limit is not None:
        budget_limit = band_limit
    elif budget_limit is not None and band_limit is not None:
        budget_limit = min(budget_limit, band_limit)
    return budget_limit


def _matches_common_filters(
    person: dict,
    assignments: list[dict],
    query: SearchQuery,
    internal_external_value: str | None = None,
) -> bool:
    top_clients = person.get("top_clients") if isinstance(person.get("top_clients"), list) else []
    top_domains = person.get("top_domains") if isinstance(person.get("top_domains"), list) else []

    person_timezone = str(person.get("timezone", ""))
    person_country = _country_from_location(str(person.get("home_location", "")))
    internal_external = str(person.get("internal_external", "internal"))
    practice = str(person.get("practice", "Unknown"))

    requested_internal_external = internal_external_value if internal_external_value else query.internal_external

    if not _matches_filter(internal_external, requested_internal_external):
        return False
    if not _matches_filter(person_country, query.country):
        return False
    if not _matches_filter(person_timezone, query.timezone):
        return False
    if not _matches_filter(practice, query.practice):
        return False

    if query.client_name:
        has_client_match = any(
            _matches_requested_name(str(item.get("client_name", "")), query.client_name)
            for item in assignments
        ) or any(_matches_requested_name(str(client), query.client_name) for client in top_clients)
        if not has_client_match:
            return False

    if query.domain_name:
        has_domain_match = any(
            _matches_requested_name(str(item.get("domain", "")), query.domain_name)
            for item in assignments
        ) or any(_matches_requested_name(str(domain), query.domain_name) for domain in top_domains)
        if not has_domain_match:
            return False

    return True


def rank_people_for_query(query: SearchQuery) -> list[Recommendation]:
    """
    Simple phase-1 ranking using sample JSON data.
    Uses lightweight lexical matching and explainability fields.
    """

    data = load_sample_data()
    scored_recommendations: list[tuple[float, Recommendation]] = []
    relationship_lookup = _build_relationship_lookup(data.relationship_edges)

    target_person_id = query.worked_with_person_id
    if not target_person_id and query.worked_with_person_name:
        target_person_id = _resolve_person_id_by_name(data.people, query.worked_with_person_name)

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

        top_clients = person.get("top_clients") if isinstance(person.get("top_clients"), list) else []
        top_domains = person.get("top_domains") if isinstance(person.get("top_domains"), list) else []

        if not _matches_common_filters(person, assignments, query):
            continue

        availability_percent = int((commercial or {}).get("availability_percent", 0))
        available_from_date = _parse_iso_date((commercial or {}).get("effective_from"))
        bill_rate = float((commercial or {}).get("bill_rate_usd", 0)) if commercial else None

        budget_limit = _effective_budget_limit(query)

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

        interviewer_suitable = bool(person.get("interviewer_suitable", False))
        willing_to_interview = bool(person.get("willing_to_interview", False))
        prior_interview_count = int(person.get("prior_interview_count", 0) or 0)
        interviewer_ready = interviewer_suitable and willing_to_interview

        willing_to_support_pocs = bool(person.get("willing_to_support_pocs", False))
        poc_participation_count = int(person.get("poc_participation_count", 0) or 0)
        presales_participation_count = int(person.get("presales_participation_count", 0) or 0)
        client_facing_comfort = str(person.get("client_facing_comfort", ""))
        client_facing_comfort_level = _client_facing_comfort_level(client_facing_comfort)
        minimum_client_facing_comfort_level = _client_facing_comfort_level(
            query.minimum_client_facing_comfort
        )

        if query.interviewer_only and not interviewer_ready:
            continue
        if (
            query.minimum_prior_interview_count is not None
            and prior_interview_count < query.minimum_prior_interview_count
        ):
            continue
        if query.poc_support_only and not willing_to_support_pocs:
            continue
        if (
            minimum_client_facing_comfort_level > 0
            and client_facing_comfort_level < minimum_client_facing_comfort_level
        ):
            continue
        if (
            query.minimum_poc_participation_count is not None
            and poc_participation_count < query.minimum_poc_participation_count
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

        confidence_score, confidence_band, freshness_summary, evidence_count = _build_confidence_layer(
            person=person,
            evidence=evidence,
            assignments=assignments,
        )
        source_mix = _build_source_mix(person, evidence, assignments, commercial)

        legacy_confidence_parts = [float(person.get("profile_confidence", 0.5))]
        legacy_confidence_parts.extend(float(item.get("confidence", 0.5)) for item in evidence)
        legacy_confidence_parts.extend(float(item.get("confidence", 0.5)) for item in assignments)
        if commercial:
            legacy_confidence_parts.append(float(commercial.get("confidence", 0.5)))

        ranking_score = round(
            sum(legacy_confidence_parts) / max(len(legacy_confidence_parts), 1),
            2,
        )
        availability_boost = _availability_rank_boost(availability_percent, available_from_date)
        budget_boost = _budget_fit_rank_boost(bill_rate, budget_limit)
        client_domain_boost, client_domain_reasons = _client_domain_rank_boost(
            assignments=assignments,
            top_clients=top_clients,
            top_domains=top_domains,
            client_name=query.client_name,
            domain_name=query.domain_name,
        )

        interviewer_boost = 0.0
        interviewer_relevant = (
            query.workflow == "interviewer_finder"
            or query.interviewer_only
            or query.minimum_prior_interview_count is not None
        )
        if interviewer_relevant and interviewer_ready:
            interviewer_boost = 0.02 + min(prior_interview_count, 10) / 1000

        poc_support_boost = 0.0
        poc_support_relevant = (
            query.workflow == "poc_support_finder"
            or query.poc_support_only
            or query.minimum_poc_participation_count is not None
        )
        if poc_support_relevant and willing_to_support_pocs:
            poc_support_boost = 0.02 + min(poc_participation_count, 10) / 1000
            if client_facing_comfort_level >= CLIENT_FACING_COMFORT_LEVELS["medium"]:
                poc_support_boost += 0.005
            if presales_participation_count > 0:
                poc_support_boost += min(presales_participation_count, 5) / 2000

        relationship_boost, relationship_context_note = _relationship_rank_boost(
            person_id=person_id,
            relationship_lookup=relationship_lookup,
            target_person_id=target_person_id,
        )

        ranking_score = round(
            min(
                1.0,
                ranking_score
                + availability_boost
                + budget_boost
                + client_domain_boost
                + interviewer_boost
                + poc_support_boost
                + relationship_boost,
            ),
            2,
        )

        why_recommended = [
            "Profile summary and project history match the current request context.",
        ]
        if evidence:
            why_recommended.append(
                f"Matched {len(evidence)} skill evidence record(s) for workflow {query.workflow}."
            )
        if assignments:
            domains = ", ".join(sorted({a.get("domain", "unknown") for a in assignments}))
            assignment_sources = sorted(
                {
                    str((a.get("source_provenance") or {}).get("source_type", "unknown")).strip().lower()
                    or "unknown"
                    for a in assignments
                }
            )
            source_label = ", ".join(assignment_sources)
            why_recommended.append(
                f"Recent assignment evidence found in domains: {domains} (sources: {source_label})."
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
        if client_domain_boost > 0:
            why_recommended.append(
                "Client/domain relevance influenced ranking with a small boost "
                f"({' and '.join(client_domain_reasons)})."
            )
        if interviewer_boost > 0:
            why_recommended.append(
                "Interviewer readiness influenced ranking with a small boost "
                f"(prior interviews: {prior_interview_count}, client-facing comfort: {person.get('client_facing_comfort', 'unknown')})."
            )
        if poc_support_boost > 0:
            why_recommended.append(
                "POC readiness influenced ranking with a small boost "
                f"(willing to support POCs: {willing_to_support_pocs}, POC participation: {poc_participation_count}, "
                f"presales participation: {presales_participation_count}, client-facing comfort: {client_facing_comfort or 'unknown'})."
            )
        if relationship_boost > 0:
            relationship_reference = query.worked_with_person_name or target_person_id or "requested person"
            relationship_reason = (
                "Relationship context influenced ranking with a small boost "
                f"(worked with: {relationship_reference}"
            )
            if relationship_context_note:
                relationship_reason += f", context: {relationship_context_note}"
            relationship_reason += ")."
            why_recommended.append(relationship_reason)

        why_recommended.append(
            "Confidence layer summary: "
            f"{confidence_band} confidence ({confidence_score}) with {evidence_count} evidence record(s); "
            f"freshness check: {freshness_summary.lower()}"
        )

        uncertainties = [
            "Validate latest availability with delivery lead before staffing.",
        ]
        if commercial and commercial.get("availability_note"):
            uncertainties.append(str(commercial["availability_note"]))

        recommendation = Recommendation(
                person_id=person_id,
                full_name=str(person.get("full_name", "Unknown")),
                role=str(person.get("current_role", "Unknown role")),
                confidence_score=confidence_score,
                confidence_band=confidence_band,
                evidence_count=evidence_count,
                freshness_summary=freshness_summary,
                source_mix=source_mix,
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
        scored_recommendations.append((ranking_score, recommendation))

    sorted_scored_recommendations = sorted(scored_recommendations, key=lambda item: item[0], reverse=True)
    return [item[1] for item in sorted_scored_recommendations]


def build_pod_for_query(query: SearchQuery) -> dict:
    """Simple explainable Phase-1 pod builder workflow using sample JSON."""

    data = load_sample_data()
    required_skills = {_normalized_text(skill) for skill in query.required_skills if skill.strip()}
    desired_roles = [_normalized_text(role) for role in query.desired_roles if role.strip()]
    pod_size = query.pod_size or 3

    internal_external_value = query.internal_external_preference or query.internal_external
    budget_limit_per_person = _effective_budget_limit(query)
    relationship_lookup = _build_relationship_lookup(data.relationship_edges)

    candidates: list[dict] = []
    for person in data.people:
        person_id = str(person.get("person_id", ""))
        assignments = [item for item in data.assignments if item.get("person_id") == person_id]
        commercial = next(
            (item for item in data.commercial_profiles if item.get("person_id") == person_id),
            None,
        )
        evidence = [item for item in data.skill_evidence if item.get("person_id") == person_id]

        if not _matches_common_filters(person, assignments, query, internal_external_value):
            continue

        availability_percent = int((commercial or {}).get("availability_percent", 0) or 0)
        available_from_date = _parse_iso_date((commercial or {}).get("effective_from"))
        bill_rate = float((commercial or {}).get("bill_rate_usd", 0) or 0)

        if (
            query.minimum_available_percent is not None
            and availability_percent < query.minimum_available_percent
        ):
            continue
        if query.available_by_date and (
            not available_from_date or available_from_date > query.available_by_date
        ):
            continue
        if budget_limit_per_person is not None and bill_rate > budget_limit_per_person:
            continue

        person_role = _normalized_text(str(person.get("current_role", "")))
        person_skill_tokens = {
            _normalized_text(str(item.get("skill_name", "")))
            for item in evidence
            if str(item.get("skill_name", "")).strip()
        }
        skill_text = _normalized_text(
            " ".join(
                [
                    str(person.get("summary", "")),
                    " ".join(str(item.get("skill_name", "")) for item in evidence),
                    " ".join(str(item.get("project_summary", "")) for item in assignments),
                ]
            )
        )

        matched_skills = {
            requested_skill
            for requested_skill in required_skills
            if requested_skill in person_skill_tokens or requested_skill in skill_text
        }
        matched_roles = {
            role for role in desired_roles if role in person_role or person_role in role
        }

        candidates.append(
            {
                "person_id": person_id,
                "full_name": str(person.get("full_name", "Unknown")),
                "current_role": str(person.get("current_role", "Unknown role")),
                "internal_external": str(person.get("internal_external", "internal")),
                "availability_percent": availability_percent,
                "available_from": available_from_date.isoformat() if available_from_date else None,
                "bill_rate_usd": bill_rate,
                "matched_skills": matched_skills,
                "matched_roles": matched_roles,
                "confidence": float(person.get("profile_confidence", 0.5)),
            }
        )

    selected: list[dict] = []
    covered_skills: set[str] = set()
    covered_roles: set[str] = set()

    remaining = candidates.copy()
    relationship_links_used = 0
    while remaining and len(selected) < pod_size:
        best = max(
            remaining,
            key=lambda c: (
                len(c["matched_skills"] - covered_skills),
                len(c["matched_roles"] - covered_roles),
                _pair_relationship_boost(c["person_id"], selected, relationship_lookup)[0]
                if query.prefer_people_who_worked_together
                else 0.0,
                c["availability_percent"],
                c["confidence"],
                -c["bill_rate_usd"],
            ),
        )
        if query.prefer_people_who_worked_together and selected:
            _, connected_edges = _pair_relationship_boost(best["person_id"], selected, relationship_lookup)
            relationship_links_used += connected_edges
        selected.append(best)
        covered_skills.update(best["matched_skills"])
        covered_roles.update(best["matched_roles"])
        remaining = [candidate for candidate in remaining if candidate["person_id"] != best["person_id"]]

    total_bill_rate = round(sum(person["bill_rate_usd"] for person in selected), 2)
    within_budget = query.budget_ceiling is None or total_bill_rate <= query.budget_ceiling

    unassigned_roles = [role for role in desired_roles if role not in covered_roles]
    role_assignments = {}
    for role in desired_roles:
        matching_person = next((person for person in selected if role in person["matched_roles"]), None)
        if matching_person:
            role_assignments[role] = matching_person["full_name"]

    for person in selected:
        assigned = next(
            (role for role, name in role_assignments.items() if name == person["full_name"]),
            None,
        )
        person["assigned_role"] = assigned

    missing_skills = [skill for skill in required_skills if skill not in covered_skills]

    backups = sorted(
        remaining,
        key=lambda c: (
            len(c["matched_skills"]),
            len(c["matched_roles"]),
            c["availability_percent"],
            c["confidence"],
        ),
        reverse=True,
    )[:2]

    constraints_satisfied: list[str] = []
    constraints_partial: list[str] = []

    if len(selected) == pod_size:
        constraints_satisfied.append(f"Pod size target met ({pod_size}).")
    else:
        constraints_partial.append(f"Only {len(selected)} person(s) matched filters out of requested {pod_size}.")

    if not missing_skills:
        constraints_satisfied.append("All required skills are covered by selected people.")
    else:
        constraints_partial.append(f"Missing required skills: {', '.join(missing_skills)}.")

    if not unassigned_roles:
        constraints_satisfied.append("All desired roles have a simple assignment.")
    else:
        constraints_partial.append(f"Roles without assignment: {', '.join(unassigned_roles)}.")

    if query.budget_ceiling is not None and within_budget:
        constraints_satisfied.append("Estimated total bill rate is within budget ceiling.")
    elif query.budget_ceiling is not None:
        constraints_partial.append("Estimated total bill rate is above budget ceiling.")

    why_this_pod = [
        "This pod was selected with a simple greedy approach to maximize skill and role coverage first.",
        "Availability and budget were used as practical Phase 1 tie-breakers.",
    ]
    if query.prefer_people_who_worked_together and relationship_links_used > 0:
        why_this_pod.append(
            "Relationship context influenced pod ranking with a small boost for people who have worked together before."
        )

    uncertainties = [
        "Budget fit uses a simple sum of sample bill rates and may need finance validation.",
        "Role assignment is based on current-role text match and should be reviewed by a delivery lead.",
        "Availability can change quickly and should be re-confirmed before client commitment.",
    ]

    return {
        "recommended_people": [
            {
                "person_id": person["person_id"],
                "full_name": person["full_name"],
                "current_role": person["current_role"],
                "assigned_role": person.get("assigned_role"),
                "internal_external": person["internal_external"],
                "availability_percent": person["availability_percent"],
                "available_from": person["available_from"],
                "bill_rate_usd": person["bill_rate_usd"],
                "matched_skills": sorted(person["matched_skills"]),
                "matched_roles": sorted(person["matched_roles"]),
            }
            for person in selected
        ],
        "coverage_summary": {
            "required_skills": sorted(required_skills),
            "covered_skills": sorted(covered_skills),
            "missing_skills": sorted(missing_skills),
            "desired_roles": desired_roles,
            "covered_roles": sorted(covered_roles),
            "unassigned_roles": unassigned_roles,
        },
        "budget_fit_summary": {
            "budget_ceiling": query.budget_ceiling,
            "estimated_total_bill_rate": total_bill_rate,
            "within_budget": within_budget,
            "notes": "Estimated total bill rate is a simple sum of selected people bill rates.",
        },
        "gaps": [
            *([f"Missing skills: {', '.join(missing_skills)}"] if missing_skills else []),
            *([f"Unassigned roles: {', '.join(unassigned_roles)}"] if unassigned_roles else []),
        ],
        "substitutions_or_backups": [
            {
                "person_id": person["person_id"],
                "full_name": person["full_name"],
                "current_role": person["current_role"],
                "matched_skills": sorted(person["matched_skills"]),
                "matched_roles": sorted(person["matched_roles"]),
            }
            for person in backups
        ],
        "why_this_pod_was_suggested": why_this_pod,
        "constraints_satisfied": constraints_satisfied,
        "constraints_partially_satisfied": constraints_partial,
        "uncertainties": uncertainties,
        "next_action": "Review this pod with a delivery manager, confirm current availability, and validate budget assumptions with finance.",
    }
