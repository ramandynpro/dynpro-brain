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


@dataclass(frozen=True)
class SampleDataConfig:
    sample_data_dir: Path
    pilot_people_data_path: Path | None
    pilot_assignments_data_path: Path | None


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

    return SampleDataConfig(
        sample_data_dir=sample_data_dir,
        pilot_people_data_path=pilot_people_data_path,
        pilot_assignments_data_path=pilot_assignments_data_path,
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
    Supports sample data and an optional pilot people file from CSV importer output.
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

    return SampleDataBundle(
        people=people,
        skill_evidence=_load_json_array(sample_dir / "skill_evidence.json"),
        assignments=assignments,
        commercial_profiles=_load_json_array(sample_dir / "commercial_profile.json"),
        relationship_edges=_load_json_array(sample_dir / "relationship_edge.json"),
        people_data_sources=people_data_sources,
        assignment_data_sources=assignment_data_sources,
    )
