import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.services.sample_data import _merge_relationship_records, load_sample_data


class TestRelationshipMergeLoader(unittest.TestCase):
    def test_relationship_records_merge_and_source_labels(self) -> None:
        merged = _merge_relationship_records(
            sample_relationships=[
                {"edge_id": "e1", "relationship_type": "worked_with", "strength": 0.2},
            ],
            pilot_relationships=[
                {"edge_id": "e1", "relationship_type": "worked_with", "strength": 0.9},
            ],
        )
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["strength"], 0.9)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            sample_dir = tmp_path / "sample_json"
            sample_dir.mkdir(parents=True, exist_ok=True)

            (sample_dir / "person.json").write_text(
                json.dumps([{"person_id": "p1", "full_name": "A", "current_role": "R", "profile_last_updated_at": "2024-01-01T00:00:00Z"}]),
                encoding="utf-8",
            )
            (sample_dir / "assignment_project.json").write_text(json.dumps([]), encoding="utf-8")
            (sample_dir / "skill_evidence.json").write_text(json.dumps([]), encoding="utf-8")
            (sample_dir / "commercial_profile.json").write_text(json.dumps([]), encoding="utf-8")
            (sample_dir / "relationship_edge.json").write_text(
                json.dumps([{"edge_id": "e1", "relationship_type": "worked_with", "strength": 0.1}]),
                encoding="utf-8",
            )

            pilot_relationship_file = tmp_path / "pilot_relationship.json"
            pilot_relationship_file.write_text(
                json.dumps([{"edge_id": "e1", "relationship_type": "worked_with", "strength": 0.95}]),
                encoding="utf-8",
            )

            original_sample_dir = settings.sample_data_dir
            original_pilot_relationship = settings.pilot_relationship_data_path
            original_pilot_people = settings.pilot_people_data_path
            original_pilot_assignments = settings.pilot_assignments_data_path
            original_pilot_skill = settings.pilot_skill_evidence_data_path
            original_pilot_commercial = settings.pilot_commercial_data_path
            try:
                settings.sample_data_dir = str(sample_dir)
                settings.pilot_relationship_data_path = str(pilot_relationship_file)
                settings.pilot_people_data_path = None
                settings.pilot_assignments_data_path = None
                settings.pilot_skill_evidence_data_path = None
                settings.pilot_commercial_data_path = None
                load_sample_data.cache_clear()

                data = load_sample_data()
                self.assertEqual(data.relationship_data_sources, ["sample", "pilot"])
                self.assertEqual(len(data.relationship_edges), 1)
                self.assertEqual(data.relationship_edges[0]["strength"], 0.95)
            finally:
                settings.sample_data_dir = original_sample_dir
                settings.pilot_relationship_data_path = original_pilot_relationship
                settings.pilot_people_data_path = original_pilot_people
                settings.pilot_assignments_data_path = original_pilot_assignments
                settings.pilot_skill_evidence_data_path = original_pilot_skill
                settings.pilot_commercial_data_path = original_pilot_commercial
                load_sample_data.cache_clear()


if __name__ == "__main__":
    unittest.main()
