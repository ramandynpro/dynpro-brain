import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.search import SearchQuery
from app.services.ranking import build_pod_for_query
from app.services.sample_data import SampleDataBundle


class TestPodBuilderUnknownBillRate(unittest.TestCase):
    def _bundle(self) -> SampleDataBundle:
        return SampleDataBundle(
            people=[
                {
                    "person_id": "p_unknown",
                    "full_name": "Unknown Rate",
                    "current_role": "Engineer",
                    "internal_external": "internal",
                    "profile_confidence": 0.95,
                },
                {
                    "person_id": "p_low",
                    "full_name": "Low Rate",
                    "current_role": "Engineer",
                    "internal_external": "internal",
                    "profile_confidence": 0.8,
                },
                {
                    "person_id": "p_mid",
                    "full_name": "Mid Rate",
                    "current_role": "Engineer",
                    "internal_external": "internal",
                    "profile_confidence": 0.7,
                },
            ],
            skill_evidence=[],
            assignments=[],
            commercial_profiles=[
                {"person_id": "p_unknown", "availability_percent": 100, "bill_rate_usd": ""},
                {"person_id": "p_low", "availability_percent": 80, "bill_rate_usd": 90},
                {"person_id": "p_mid", "availability_percent": 70, "bill_rate_usd": 95},
            ],
            relationship_edges=[],
            people_data_sources=["sample"],
            assignment_data_sources=["sample"],
            skill_evidence_data_sources=["sample"],
            commercial_data_sources=["sample"],
            relationship_data_sources=["sample"],
        )

    def test_unknown_bill_rate_behavior_for_budget_handling(self) -> None:
        with patch("app.services.ranking.load_sample_data", return_value=self._bundle()):
            no_budget_query = SearchQuery(workflow="pod_builder", text_query="build pod", pod_size=1)
            no_budget_result = build_pod_for_query(no_budget_query)

            selected = no_budget_result["recommended_people"]
            self.assertIsNone(selected[0]["bill_rate_usd"])
            self.assertEqual(no_budget_result["budget_fit_summary"]["unknown_bill_rate_count"], 1)
            self.assertIsNone(no_budget_result["budget_fit_summary"]["estimated_total_bill_rate"])

            budgeted_query = SearchQuery(
                workflow="pod_builder",
                text_query="build pod",
                pod_size=2,
                max_bill_rate=100,
            )
            budgeted_result = build_pod_for_query(budgeted_query)

            selected_ids = {person["person_id"] for person in budgeted_result["recommended_people"]}
            self.assertNotIn("p_unknown", selected_ids)
            self.assertEqual(budgeted_result["budget_fit_summary"]["unknown_bill_rate_count"], 0)


if __name__ == "__main__":
    unittest.main()
