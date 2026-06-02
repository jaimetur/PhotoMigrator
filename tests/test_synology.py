import unittest

from Features.SynologyPhotos.ClassSynologyPhotos import ClassSynologyPhotos


class TestSynologyPhotosUnit(unittest.TestCase):
    def setUp(self):
        self.manager = ClassSynologyPhotos.__new__(ClassSynologyPhotos)

    def test_filter_assets_by_type_supports_photo_aliases_and_live_assets(self):
        assets = [
            {"id": "1", "type": "PHOTO"},
            {"id": "2", "type": "LIVE"},
            {"id": "3", "type": "VIDEO"},
        ]

        filtered = self.manager.filter_assets_by_type(assets, "photos")

        self.assertEqual([asset["id"] for asset in filtered], ["1", "2"])

    def test_filter_assets_by_date_respects_epoch_range(self):
        assets = [
            {"id": "old", "time": 100},
            {"id": "inside", "time": 200},
            {"id": "new", "time": 300},
        ]

        filtered = self.manager.filter_assets_by_date(assets, from_date=150, to_date=250)

        self.assertEqual([asset["id"] for asset in filtered], ["inside"])

    def test_filter_assets_by_place_matches_nested_address_values(self):
        assets = [
            {"id": "1", "additional": {"address": {"city": "Madrid"}}},
            {"id": "2", "additional": {"address": {"country": "Spain"}}},
            {"id": "3", "additional": {"address": {"city": "Berlin"}}},
        ]

        filtered = self.manager.filter_assets_by_place(assets, "spa")

        self.assertEqual([asset["id"] for asset in filtered], ["2"])


if __name__ == "__main__":
    unittest.main()
