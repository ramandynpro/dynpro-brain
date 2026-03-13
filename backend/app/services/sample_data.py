from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SampleDataBundle:
    people: list[dict[str, Any]]
    skill_evidence: list[dict[str, Any]]
    assignments: list[dict[str, Any]]
    commercial_profiles: list[dict[str, Any]]
    relationship_edges: list[dict[str, Any]]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_json_array(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, list):
        raise ValueError(f"Expected a JSON array in {path}")

    return [item for item in payload if isinstance(item, dict)]


@lru_cache(maxsize=1)
def load_sample_data() -> SampleDataBundle:
    """
    Load Phase-1 sample JSON once per process.
    Data remains easy to inspect and replace while we are pre-database.
    """

    sample_dir = _repo_root() / "data" / "sample_json"

    return SampleDataBundle(
        people=_load_json_array(sample_dir / "person.json"),
        skill_evidence=_load_json_array(sample_dir / "skill_evidence.json"),
        assignments=_load_json_array(sample_dir / "assignment_project.json"),
        commercial_profiles=_load_json_array(sample_dir / "commercial_profile.json"),
        relationship_edges=_load_json_array(sample_dir / "relationship_edge.json"),
    )
