from datetime import UTC, datetime

from app.models.search import Recommendation, SearchQuery
from app.services.sample_data import load_sample_data


def _contains_any(haystack: str, needles: list[str]) -> bool:
    if not needles:
        return True
    haystack_lower = haystack.lower()
    return any(needle.lower() in haystack_lower for needle in needles)


def _parse_last_updated(value: str | None) -> datetime:
    if not value:
        return datetime.now(UTC)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


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
