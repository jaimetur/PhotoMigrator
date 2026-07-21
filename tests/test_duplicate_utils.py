import unittest
from datetime import datetime, timezone

from Utils.DuplicateUtils import duplicate_asset_people_count, select_people_then_chronology_keeper


class TestDuplicateKeeperUtils(unittest.TestCase):
    def test_people_count_uses_distinct_person_ids(self):
        asset = {
            "people": [
                {"personId": "ana"},
                {"person": {"id": "ana"}},
                {"person": {"id": "luis"}},
            ]
        }
        self.assertEqual(duplicate_asset_people_count(asset), 2)

    def test_people_count_falls_back_to_takeout_people_tags(self):
        self.assertEqual(
            duplicate_asset_people_count({"tags": [{"value": "people/Ana"}, {"value": "people/Luis"}]}),
            2,
        )

    def test_more_people_then_newest_prefers_people_before_date(self):
        older_with_people = {
            "id": "older", "people": [{"personId": "ana"}, {"personId": "luis"}],
            "created": "2020-01-01T00:00:00Z",
        }
        newer_without_people = {"id": "newer", "people": [], "created": "2024-01-01T00:00:00Z"}

        keeper = select_people_then_chronology_keeper(
            [older_with_people, newer_without_people],
            "more-people/tags-then-newest",
            lambda asset: datetime.fromisoformat(asset["created"].replace("Z", "+00:00")).astimezone(timezone.utc),
        )

        self.assertEqual(keeper["id"], "older")

    def test_more_people_then_oldest_uses_oldest_for_equal_people_counts(self):
        first = {"id": "first", "people": [{"personId": "ana"}], "time": 1}
        second = {"id": "second", "people": [{"personId": "luis"}], "time": 2}
        keeper = select_people_then_chronology_keeper(
            [second, first], "more-people/tags-then-oldest", lambda asset: asset["time"],
        )
        self.assertEqual(keeper["id"], "first")

    def test_people_tags_then_newest_uses_tag_count_before_date(self):
        more_tags = {"id": "more-tags", "people": [{"personId": "ana"}], "tags": ["a", "b"], "time": 1}
        newer = {"id": "newer", "people": [{"personId": "luis"}], "tags": ["a"], "time": 2}
        keeper = select_people_then_chronology_keeper(
            [newer, more_tags], "more-people/tags-then-newest", lambda asset: asset["time"],
        )
        self.assertEqual(keeper["id"], "more-tags")
