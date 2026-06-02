import unittest

from Features.ImmichPhotos.ClassImmichPhotos import ClassImmichPhotos


class TestImmichPhotosUnit(unittest.TestCase):
    def setUp(self):
        self.manager = ClassImmichPhotos.__new__(ClassImmichPhotos)

    def test_filter_assets_by_type_supports_aliases(self):
        assets = [
            {"id": "1", "type": "IMAGE"},
            {"id": "2", "type": "VIDEO"},
            {"id": "3", "type": "image"},
        ]

        filtered = self.manager.filter_assets_by_type(assets, "photos")

        self.assertEqual([asset["id"] for asset in filtered], ["1", "3"])

    def test_normalize_burst_stem_removes_common_suffixes(self):
        normalized = self.manager._normalize_burst_stem("IMG_1234-edited.BURST0001.jpg")
        self.assertEqual(normalized, "img_1234")

    def test_burst_primary_sort_key_prefers_image_then_larger_file(self):
        image_record = {"ext": ".jpg", "file_size": 300, "capture_epoch": 100}
        raw_record = {"ext": ".dng", "file_size": 500, "capture_epoch": 90}
        smaller_image = {"ext": ".jpg", "file_size": 200, "capture_epoch": 80}

        self.assertLess(
            self.manager._burst_primary_sort_key(image_record),
            self.manager._burst_primary_sort_key(raw_record),
        )
        self.assertLess(
            self.manager._burst_primary_sort_key(image_record),
            self.manager._burst_primary_sort_key(smaller_image),
        )


if __name__ == "__main__":
    unittest.main()
