import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.routes.search import search_people
from app.models.search import SearchQuery


class TestSearchResponseShape(unittest.TestCase):
    def test_phase1_search_response_shape_smoke(self) -> None:
        response = search_people(SearchQuery(text_query="Find Python expert"))

        self.assertIsNotNone(response.query)
        self.assertIsInstance(response.recommendations, list)
        self.assertIsInstance(response.notes, list)
        self.assertIsInstance(response.data_sources, list)
        self.assertIn(response.viewer_mode, {"broad_user", "commercial_aware"})
        self.assertIsInstance(response.commercial_masking_applied, bool)

        self.assertGreater(len(response.recommendations), 0)
        top = response.recommendations[0]
        self.assertTrue(top.why_recommended)
        self.assertIsInstance(top.uncertainties, list)
        self.assertTrue(top.next_action)


if __name__ == "__main__":
    unittest.main()
