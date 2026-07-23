import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from Utils.DuplicateUtils import (
    duplicate_asset_people_count,
    run_duplicate_asset_cleanup,
    select_people_then_chronology_keeper,
)


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

    def test_people_count_does_not_treat_people_tags_as_native_people(self):
        self.assertEqual(
            duplicate_asset_people_count({"tags": [{"value": "people/Ana"}, {"value": "people/Luis"}]}),
            0,
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

    def test_immich_cleanup_restores_detailed_duplicate_review_table(self):
        duplicate_group = [
            {
                "id": "older",
                "originalFileName": "IMG_0001.JPG",
                "createdAt": "2020-01-01T00:00:00Z",
                "dateTimeOriginal": "2019-12-31T12:00:00Z",
                "visibility": "timeline",
                "tags": [{"id": "tag-1", "value": "family/yoli"}],
                "people": [{"id": "person-1", "name": "Yoli"}],
                "exifInfo": {"fileSize": 42, "description": "Keeper description"},
            },
            {
                "id": "newer",
                "originalFileName": "IMG_0001.JPG",
                "createdAt": "2021-01-01T00:00:00Z",
                "dateTimeOriginal": "2020-01-01T12:00:00Z",
                "visibility": "timeline",
                "exifInfo": {"fileSize": 42},
                "isFavorite": True,
            },
        ]
        client = MagicMock()
        client.find_duplicate_assets_by_immich_detection.return_value = [duplicate_group]
        client.hydrate_duplicate_groups_metadata.return_value = [duplicate_group]
        client.get_duplicate_metadata_display_names.return_value = {"albums": {}, "tags": {}, "people": {}}
        client._select_duplicate_asset_keeper.return_value = duplicate_group[0]
        client._duplicate_asset_size.side_effect = lambda asset: asset["exifInfo"]["fileSize"]
        client.remove_duplicates_assets_by_name_and_size.return_value = (1, 1, 0)
        logger = MagicMock()

        run_duplicate_asset_cleanup(
            client,
            keeper_strategy="oldest",
            request_user_confirmation=False,
            use_immich_detection=True,
            use_immich_deletion=False,
            is_immich_client=True,
            logger=logger,
        )

        rendered = "\n".join(str(call.args[0]) for call in logger.info.call_args_list)
        self.assertIn("Duplicate review: 1 duplicate group(s), 2 duplicate asset(s).", rendered)
        preview_header_index = next(
            index for index, call in enumerate(logger.info.call_args_list)
            if "[1] IMG_0001.JPG" in str(call.args[0])
        )
        self.assertEqual(logger.info.call_args_list[preview_header_index - 1].args[0], "")
        self.assertIn("[1] IMG_0001.JPG (42 bytes, 2 candidate asset(s))", rendered)
        self.assertIn("Field", rendered)
        self.assertIn("Keeper (oldest)", rendered)
        self.assertIn("Remove 1", rendered)
        self.assertIn("ID", rendered)
        self.assertIn("older", rendered)
        self.assertIn("newer", rendered)
        self.assertIn("Date/time original", rendered)
        self.assertIn("Keeper description", rendered)
        self.assertIn("Favorite", rendered)
        self.assertLess(rendered.index("Tags"), rendered.index("People"))
        header = next(line for line in rendered.splitlines() if "Keeper (oldest)" in line)
        self.assertIn("Keeper (oldest)".ljust(47), header)
