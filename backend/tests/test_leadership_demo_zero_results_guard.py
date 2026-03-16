import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "frontend"))

from leadership_demo import select_leadership_demo_result


class TestLeadershipDemoZeroResultsGuard(unittest.TestCase):
    def test_returns_none_when_recommendations_is_empty(self) -> None:
        result_type, result = select_leadership_demo_result(
            "expert_finder",
            {"recommendations": []},
        )

        self.assertEqual(result_type, "none")
        self.assertIsNone(result)

    def test_returns_first_recommendation_when_available(self) -> None:
        result_type, result = select_leadership_demo_result(
            "expert_finder",
            {"recommendations": [{"full_name": "A"}, {"full_name": "B"}]},
        )

        self.assertEqual(result_type, "recommendation")
        self.assertEqual(result, {"full_name": "A"})

    def test_prefers_pod_recommendation_for_pod_builder(self) -> None:
        pod = {"recommended_people": [{"full_name": "P"}]}
        result_type, result = select_leadership_demo_result(
            "pod_builder",
            {"pod_recommendation": pod, "recommendations": [{"full_name": "Fallback"}]},
        )

        self.assertEqual(result_type, "pod")
        self.assertEqual(result, pod)


if __name__ == "__main__":
    unittest.main()
