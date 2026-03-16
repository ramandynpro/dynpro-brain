from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import settings


@dataclass(frozen=True)
class SampleDataBundle:
    people: list[dict[str, Any]]
    skill_evidence: list[dict[str, Any]]
    assignments: list[dict[str, Any]]
    commercial_profiles: list[dict[str, Any]]
    relationship_edges: list[dict[str, Any]]
    people_data_sources: list[str]
    assignment_data_sources: list[str]
    skill_evidence_data_sources: list[str]
    commercial_data_sources: list[str]
    relationship_data_sources: list[str]


@dataclass(frozen=True)
class SampleDataConfig:
    sample_data_dir: Path
    pilot_people_data_path: Path | None
    pilot_assignments_data_path: Path | None
    pilot_skill_evidence_data_path: Path | None
    pilot_commercial_data_path: Path | None
    pilot_relationship_data_path: Path | None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_sample_data_config() -> SampleDataConfig:
    repo_root = _repo_root()
    sample_data_dir = Path(settings.sample_data_dir)
    if not sample_data_dir.is_absolute():
        sample_data_dir = repo_root / sample_data_dir

    pilot_people_data_path: Path | None = None
    if settings.pilot_people_data_path:
        pilot_people_data_path = Path(settings.pilot_people_data_path)
        if not pilot_people_data_path.is_absolute():
            pilot_people_data_path = repo_root / pilot_people_data_path

    pilot_assignments_data_path: Path | None = None
    if settings.pilot_assignments_data_path:
        pilot_assignments_data_path = Path(settings.pilot_assignments_data_path)
        if not pilot_assignments_data_path.is_absolute():
            pilot_assignments_data_path = repo_root / pilot_assignments_data_path

    pilot_skill_evidence_data_path: Path | None = None
    if settings.pilot_skill_evidence_data_path:
        pilot_skill_evidence_data_path = Path(settings.pilot_skill_evidence_data_path)
        if not pilot_skill_evidence_data_path.is_absolute():
            pilot_skill_evidence_data_path = repo_root / pilot_skill_evidence_data_path

    pilot_commercial_data_path: Path | None = None
    if settings.pilot_commercial_data_path:
        pilot_commercial_data_path = Path(settings.pilot_commercial_data_path)
        if not pilot_commercial_data_path.is_absolute():
            pilot_commercial_data_path = repo_root / pilot_commercial_data_path

    pilot_relationship_data_path: Path | None = None
    if settings.pilot_relationship_data_path:
        pilot_relationship_data_path = Path(settings.pilot_relationship_data_path)
        if not pilot_relationship_data_path.is_absolute():
            pilot_relationship_data_path = repo_root / pilot_relationship_data_path

    return SampleDataConfig(
        sample_data_dir=sample_data_dir,
        pilot_people_data_path=pilot_people_data_path,
        pilot_assignments_data_path=pilot_assignments_data_path,
        pilot_skill_evidence_data_path=pilot_skill_evidence_data_path,
        pilot_commercial_data_path=pilot_commercial_data_path,
        pilot_relationship_data_path=pilot_relationship_data_path,
    )


def _load_json_array(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, list):
        raise ValueError(f"Expected a JSON array in {path}")

    return [item for item in payload if isinstance(item, dict)]


def _merge_people_records(sample_people: list[dict[str, Any]], pilot_people: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged_by_id: dict[str, dict[str, Any]] = {}

    for person in sample_people:
        person_id = str(person.get("person_id", "")).strip()
        if not person_id:
            continue
        merged_by_id[person_id] = person

    for person in pilot_people:
        person_id = str(person.get("person_id", "")).strip()
        if not person_id:
            continue
        # Keep Phase 1 behavior simple: pilot people replace sample records with same person_id.
        merged_by_id[person_id] = person

    return list(merged_by_id.values())


def _assignment_id(assignment: dict[str, Any]) -> str:
    return str(assignment.get("project_id") or assignment.get("assignment_id") or "").strip()


def _skill_evidence_id(evidence: dict[str, Any]) -> str:
    return str(evidence.get("evidence_id") or evidence.get("skill_evidence_id") or "").strip()


def _relationship_edge_id(edge: dict[str, Any]) -> str:
    return str(edge.get("edge_id") or "").strip()


def _merge_relationship_records(
    sample_relationships: list[dict[str, Any]],
    pilot_relationships: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged_by_id: dict[str, dict[str, Any]] = {}

    for edge in sample_relationships:
        edge_id = _relationship_edge_id(edge)
        if not edge_id:
            continue
        merged_by_id[edge_id] = edge

    for edge in pilot_relationships:
        edge_id = _relationship_edge_id(edge)
        if not edge_id:
            continue
        merged_by_id[edge_id] = edge

    return list(merged_by_id.values())


def _merge_assignment_records(
    sample_assignments: list[dict[str, Any]],
    pilot_assignments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged_by_id: dict[str, dict[str, Any]] = {}

    for assignment in sample_assignments:
        assignment_id = _assignment_id(assignment)
        if not assignment_id:
            continue
        merged_by_id[assignment_id] = assignment

    for assignment in pilot_assignments:
        assignment_id = _assignment_id(assignment)
        if not assignment_id:
            continue
        merged_by_id[assignment_id] = assignment

    return list(merged_by_id.values())


@lru_cache(maxsize=1)
def load_sample_data() -> SampleDataBundle:
    """
    Load Phase-1 local JSON once per process.
    Supports sample data and optional pilot people, assignment/project, skill-evidence, and commercial files from CSV importer output.
    """

    data_config = _resolve_sample_data_config()
    sample_dir = data_config.sample_data_dir

    sample_people = _load_json_array(sample_dir / "person.json")

    people_data_sources = ["sample"]
    if data_config.pilot_people_data_path and data_config.pilot_people_data_path.exists():
        pilot_people = _load_json_array(data_config.pilot_people_data_path)
        people = _merge_people_records(sample_people=sample_people, pilot_people=pilot_people)
        people_data_sources.append("pilot")
    else:
        people = sample_people

    sample_assignments = _load_json_array(sample_dir / "assignment_project.json")
    sample_skill_evidence = _load_json_array(sample_dir / "skill_evidence.json")

    assignment_data_sources = ["sample"]
    if data_config.pilot_assignments_data_path and data_config.pilot_assignments_data_path.exists():
        pilot_assignments = _load_json_array(data_config.pilot_assignments_data_path)
        assignments = _merge_assignment_records(
            sample_assignments=sample_assignments,
            pilot_assignments=pilot_assignments,
        )
        assignment_data_sources.append("pilot")
    else:
        assignments = sample_assignments

    skill_evidence_data_sources = ["sample"]
    if data_config.pilot_skill_evidence_data_path and data_config.pilot_skill_evidence_data_path.exists():
        pilot_skill_evidence = _load_json_array(data_config.pilot_skill_evidence_data_path)
        skill_evidence = _merge_skill_evidence_records(
            sample_skill_evidence=sample_skill_evidence,
            pilot_skill_evidence=pilot_skill_evidence,
        )
        skill_evidence_data_sources.append("pilot")
    else:
        skill_evidence = sample_skill_evidence

    sample_commercial_profiles = _load_json_array(sample_dir / "commercial_profile.json")
    commercial_data_sources = ["sample"]
    if data_config.pilot_commercial_data_path and data_config.pilot_commercial_data_path.exists():
        pilot_commercial_profiles = _load_json_array(data_config.pilot_commercial_data_path)
        commercial_profiles = _merge_commercial_records(
            sample_commercial_profiles=sample_commercial_profiles,
            pilot_commercial_profiles=pilot_commercial_profiles,
        )
        commercial_data_sources.append("pilot")
    else:
        commercial_profiles = sample_commercial_profiles

    sample_relationships = _load_json_array(sample_dir / "relationship_edge.json")
    relationship_data_sources = ["sample"]
    if data_config.pilot_relationship_data_path and data_config.pilot_relationship_data_path.exists():
        pilot_relationships = _load_json_array(data_config.pilot_relationship_data_path)
        relationship_edges = _merge_relationship_records(
            sample_relationships=sample_relationships,
            pilot_relationships=pilot_relationships,
        )
        relationship_data_sources.append("pilot")
    else:
        relationship_edges = sample_relationships

    return SampleDataBundle(
        people=people,
        skill_evidence=skill_evidence,
        assignments=assignments,
        commercial_profiles=commercial_profiles,
        relationship_edges=relationship_edges,
        people_data_sources=people_data_sources,
        assignment_data_sources=assignment_data_sources,
        skill_evidence_data_sources=skill_evidence_data_sources,
        commercial_data_sources=commercial_data_sources,
        relationship_data_sources=relationship_data_sources,
    )


def _merge_skill_evidence_records(
    sample_skill_evidence: list[dict[str, Any]],
    pilot_skill_evidence: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged_by_id: dict[str, dict[str, Any]] = {}

    for evidence in sample_skill_evidence:
        evidence_id = _skill_evidence_id(evidence)
        if not evidence_id:
            continue
        merged_by_id[evidence_id] = evidence

    for evidence in pilot_skill_evidence:
        evidence_id = _skill_evidence_id(evidence)
        if not evidence_id:
            continue
        merged_by_id[evidence_id] = evidence

    return list(merged_by_id.values())


def _commercial_profile_id(profile: dict[str, Any]) -> str:
    return str(profile.get("commercial_profile_id") or profile.get("commercial_id") or "").strip()


def _merge_commercial_records(
    sample_commercial_profiles: list[dict[str, Any]],
    pilot_commercial_profiles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged_by_id: dict[str, dict[str, Any]] = {}

    for profile in sample_commercial_profiles:
        commercial_id = _commercial_profile_id(profile)
        if not commercial_id:
            continue
        merged_by_id[commercial_id] = profile

    for profile in pilot_commercial_profiles:
        commercial_id = _commercial_profile_id(profile)
        if not commercial_id:
            continue
        merged_by_id[commercial_id] = profile

    return list(merged_by_id.values())
