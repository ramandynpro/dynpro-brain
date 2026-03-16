import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.pilot_tracking import get_data_quality_summary
from app.services.sample_data import SampleDataBundle


class TestDataQualityCommercialLookup(unittest.TestCase):
    def test_missing_counts_are_based_on_linked_commercial_profile(self) -> None:
        bundle = SampleDataBundle(
            people=[
                {
                    "person_id": "p1",
                    "full_name": "Person One",
                    "current_role": "Engineer",
                    "profile_last_updated_at": "2024-01-01T00:00:00Z",
                    "timezone": "UTC",
                    "home_location": "London, UK",
                    "practice": "Engineering",
                    "availability_percent": 100,
                    "bill_rate_usd": 120,
                },
                {
                    "person_id": "p2",
                    "full_name": "Person Two",
                    "current_role": "Engineer",
                    "profile_last_updated_at": "2024-01-01T00:00:00Z",
                    "timezone": "UTC",
                    "home_location": "London, UK",
                    "practice": "Engineering",
                },
                {
                    "person_id": "p3",
                    "full_name": "Person Three",
                    "current_role": "Engineer",
                    "profile_last_updated_at": "2024-01-01T00:00:00Z",
                    "timezone": "UTC",
                    "home_location": "London, UK",
                    "practice": "Engineering",
                },
            ],
            skill_evidence=[],
            assignments=[],
            commercial_profiles=[
                {
                    "person_id": "p2",
                    "availability_percent": 70,
                    "bill_rate_usd": 110,
                }
            ],
            relationship_edges=[],
            people_data_sources=["sample"],
            assignment_data_sources=["sample"],
            skill_evidence_data_sources=["sample"],
            commercial_data_sources=["sample"],
            relationship_data_sources=["sample"],
        )

        with patch("app.services.pilot_tracking.load_sample_data", return_value=bundle):
            summary = get_data_quality_summary()

        self.assertEqual(summary.missing_availability_field_count, 2)
        self.assertEqual(summary.missing_commercial_field_count, 2)


if __name__ == "__main__":
    unittest.main()
