import sys
import types
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

if "piexif" not in sys.modules:
    piexif_stub = types.ModuleType("piexif")
    piexif_stub.ExifIFD = types.SimpleNamespace(DateTimeOriginal=36867, DateTimeDigitized=36868)
    piexif_stub.ImageIFD = types.SimpleNamespace(DateTime=306)
    piexif_stub.load = lambda *args, **kwargs: {"0th": {}, "Exif": {}}
    piexif_stub.dump = lambda *args, **kwargs: b""
    piexif_stub.insert = lambda *args, **kwargs: None
    sys.modules["piexif"] = piexif_stub

if "colorama" not in sys.modules:
    colorama_stub = types.ModuleType("colorama")
    colorama_stub.init = lambda *args, **kwargs: None
    colorama_stub.Fore = types.SimpleNamespace(RED="", GREEN="", YELLOW="", CYAN="", WHITE="", BLUE="", MAGENTA="")
    colorama_stub.Style = types.SimpleNamespace(RESET_ALL="", BRIGHT="", DIM="", NORMAL="")
    sys.modules["colorama"] = colorama_stub

try:
    import Core.GlobalVariables as GV
    from Utils.GeneralUtils import (
        match_pattern,
        replace_pattern,
        confirm_continue,
        has_any_filter,
        normalize_album_name_for_matching,
        find_reusable_album_candidate,
        build_reusable_album_group,
        scan_album_consolidation_groups,
    )
    GENERAL_UTILS_IMPORT_ERROR = None
except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
    GENERAL_UTILS_IMPORT_ERROR = exc


class TestGeneralUtilsPatterns(unittest.TestCase):
    def setUp(self):
        if GENERAL_UTILS_IMPORT_ERROR is not None:
            self.skipTest(f"GeneralUtils dependencies are not installed in this environment: {GENERAL_UTILS_IMPORT_ERROR}")

    def test_replace_pattern_supports_literal_replacement(self):
        self.assertEqual(replace_pattern("Trip -- Summer", "--", "-"), "Trip - Summer")

    def test_match_pattern_supports_literal_matching(self):
        self.assertTrue(match_pattern("Temp Album", "Temp"))

    def test_match_pattern_supports_wildcard_matching(self):
        self.assertTrue(match_pattern("Holiday--Draft", "*--*"))

    def test_replace_pattern_supports_wildcard_replacement_in_middle(self):
        self.assertEqual(replace_pattern("Trip--Summer--2026", "*--*", "-"), "Trip-Summer-2026")

    def test_replace_pattern_wildcard_with_same_replacement_keeps_original_text(self):
        self.assertEqual(replace_pattern("2025-12-20 - Viaje", "*-*", "-"), "2025-12-20 - Viaje")

    def test_replace_pattern_supports_wildcard_replacement_at_start(self):
        self.assertEqual(replace_pattern("--Trip--Summer", "--*", "-"), "-Trip--Summer")

    def test_replace_pattern_supports_wildcard_replacement_at_end(self):
        self.assertEqual(replace_pattern("Trip--Summer--", "*--", "-"), "Trip--Summer-")

    def test_replace_pattern_keeps_regex_replacement_support(self):
        self.assertEqual(
            replace_pattern("2026.07.06 - Summer", r"\b(\d{4})\.(\d{2})\.(\d{2})\b", r"\1-\2-\3"),
            "2026-07-06 - Summer",
        )

    def test_normalize_album_name_for_matching_collapses_harmless_separator_differences(self):
        self.assertEqual(
            normalize_album_name_for_matching("2026.07.06 -- Viaje a Roma"),
            normalize_album_name_for_matching("2026-07-06 — Viaje   a  Roma"),
        )

    def test_find_reusable_album_candidate_returns_unique_similar_match_when_enabled(self):
        album, match_kind, ambiguous = find_reusable_album_candidate(
            album_name="2026.07.06 -- Viaje a Roma",
            albums=[{"id": "album-1", "albumName": "2026-07-06 - Viaje a Roma"}],
            allow_similar=True,
            exact_case_sensitive=False,
        )

        self.assertEqual(album, {"id": "album-1", "albumName": "2026-07-06 - Viaje a Roma"})
        self.assertEqual(match_kind, "similar")
        self.assertEqual(ambiguous, [])

    def test_find_reusable_album_candidate_reports_ambiguous_similar_matches(self):
        album, match_kind, ambiguous = find_reusable_album_candidate(
            album_name="2026.07.06 -- Viaje a Roma",
            albums=[
                {"id": "album-1", "albumName": "2026-07-06 - Viaje a Roma"},
                {"id": "album-2", "albumName": "2026 07 06 Viaje a Roma"},
            ],
            allow_similar=True,
            exact_case_sensitive=False,
        )

        self.assertIsNone(album)
        self.assertIsNone(match_kind)
        self.assertEqual(len(ambiguous), 2)

    def test_build_reusable_album_group_prefers_normalized_name_even_without_existing_redundancy(self):
        plan = build_reusable_album_group(
            album_name="Huelva_1",
            albums=[],
            allow_similar=True,
            exact_case_sensitive=False,
        )

        self.assertIsNone(plan["matched_album"])
        self.assertEqual(plan["preferred_album_name"], "Huelva")
        self.assertTrue(plan["should_create_preferred_album"])

    def test_scan_album_consolidation_groups_keeps_the_most_precise_compatible_date(self):
        groups = scan_album_consolidation_groups([
            {"id": "year", "albumName": "2020 - Album1"},
            {"id": "month", "albumName": "2020.06 -- Album1"},
            {"id": "other-year", "albumName": "2021-04 - Album1"},
        ])

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["reason"], "date-prefix")
        self.assertEqual(groups[0]["keeper_album"]["id"], "month")
        self.assertEqual({album["id"] for album in groups[0]["similar_albums"]}, {"year", "month"})

    def test_scan_album_consolidation_groups_does_not_bridge_conflicting_precise_dates(self):
        groups = scan_album_consolidation_groups([
            {"id": "year", "albumName": "2020 - Album1"},
            {"id": "june", "albumName": "2020-06 - Album1"},
            {"id": "july", "albumName": "2020-07 - Album1"},
        ])

        self.assertEqual(groups, [])

    def test_date_prefix_prefers_specific_keeper_when_all_its_assets_fit_the_day(self):
        groups = scan_album_consolidation_groups(
            [
                {"id": "month", "albumName": "2012-08 - Feria de Málaga"},
                {"id": "day", "albumName": "2012-08-15 - Feria de Málaga"},
            ],
            asset_dates_getter=lambda album: {
                "month": [datetime(2012, 8, 1), datetime(2012, 8, 15)],
                "day": [datetime(2012, 8, 15), datetime(2012, 8, 15, 20)],
            }[album["id"]],
        )

        self.assertEqual(groups[0]["keeper_album"]["id"], "day")
        self.assertTrue(groups[0]["assets_date_considered"])

    def test_date_prefix_prefers_specific_keeper_when_at_least_95_percent_fit_the_day(self):
        groups = scan_album_consolidation_groups(
            [
                {"id": "month", "albumName": "2012-08 - Feria de Málaga"},
                {"id": "day", "albumName": "2012-08-15 - Feria de Málaga"},
            ],
            asset_dates_getter=lambda album: {
                "month": [datetime(2012, 8, 1), datetime(2012, 8, 15)],
                "day": [datetime(2012, 8, 15)] * 19 + [datetime(2012, 8, 16)],
            }[album["id"]],
        )

        self.assertEqual(groups[0]["keeper_album"]["id"], "day")
        self.assertTrue(groups[0]["assets_date_considered"])

    def test_date_prefix_prefers_broader_keeper_below_95_percent_fit(self):
        groups = scan_album_consolidation_groups(
            [
                {"id": "month", "albumName": "2012-08 - Feria de Málaga"},
                {"id": "day", "albumName": "2012-08-15 - Feria de Málaga"},
            ],
            asset_dates_getter=lambda album: {
                "month": [datetime(2012, 8, 1), datetime(2012, 8, 15)],
                "day": [datetime(2012, 8, 15)] * 18 + [datetime(2012, 8, 16)] * 2,
            }[album["id"]],
        )

        self.assertEqual(groups[0]["keeper_album"]["id"], "month")
        self.assertTrue(groups[0]["assets_date_considered"])

    def test_scan_album_consolidation_groups_merges_truncated_names_for_same_dominant_year(self):
        assets_by_id = {
            "full": [{"fileCreatedAt": "2024-07-03T10:00:00Z"}, {"fileCreatedAt": "2024-07-04T10:00:00Z"}],
            "cut": [{"fileCreatedAt": "2024-07-05T10:00:00Z"}, {"fileCreatedAt": "2024-08-01T10:00:00Z"}],
        }
        groups = scan_album_consolidation_groups(
            [
                {"id": "full", "albumName": "Viaje con María"},
                {"id": "cut", "albumName": "Viaje con Ma"},
            ],
            asset_years_getter=lambda album: [int(asset["fileCreatedAt"][:4]) for asset in assets_by_id[album["id"]]],
        )

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["reason"], "truncated-name")
        self.assertEqual(groups[0]["keeper_album"]["id"], "full")

    def test_scan_album_consolidation_groups_does_not_treat_a_bare_year_as_a_truncated_name(self):
        groups = scan_album_consolidation_groups(
            [
                {"id": "year", "albumName": "2015"},
                {"id": "madrid", "albumName": "2015-05-21 - Con Yraly por Madrid"},
                {"id": "praga", "albumName": "2015 - Viaje - 1.Praga"},
            ],
            asset_years_getter=lambda _album: [2015, 2015],
        )

        self.assertEqual(groups, [])

    def test_scan_album_consolidation_groups_requires_two_distinct_words_for_truncation(self):
        groups = scan_album_consolidation_groups(
            [
                {"id": "base", "albumName": "Casa"},
                {"id": "rural", "albumName": "Casa rural"},
                {"id": "blanca", "albumName": "Casa blanca"},
            ],
            asset_years_getter=lambda _album: [2024, 2024],
        )

        self.assertEqual(groups, [])

    def test_scan_album_consolidation_groups_prefers_non_videos_keeper_for_truncation(self):
        groups = scan_album_consolidation_groups(
            [
                {"id": "plain", "albumName": "2013-12-31 - Fiesta de Fin de Año"},
                {"id": "videos", "albumName": "2013-12-31 - Fiesta de Fin de Año Videos"},
            ],
            asset_years_getter=lambda _album: [2013, 2013],
        )

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["keeper_album"]["id"], "plain")
        self.assertEqual(groups[0]["reason"], "truncated-name-grouping-videos")

    def test_scan_album_consolidation_groups_prefers_without_redundant_terminal_date(self):
        groups = scan_album_consolidation_groups(
            [
                {"id": "plain", "albumName": "2019-2021 - Piso Habitat Litoral Málaga"},
                {"id": "redundant", "albumName": "2019-2021 - Piso Habitat Litoral Málaga 2020"},
            ],
            asset_years_getter=lambda _album: [2020, 2020],
        )

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["keeper_album"]["id"], "plain")
        self.assertEqual(groups[0]["reason"], "truncated-name-redundant-date")

    def test_scan_album_consolidation_groups_does_not_block_same_year_truncation_for_another_year(self):
        groups = scan_album_consolidation_groups(
            [
                {"id": "full", "albumName": "Viaje con María"},
                {"id": "cut", "albumName": "Viaje con Ma"},
                {"id": "other-year", "albumName": "Viaje con M"},
            ],
            asset_years_getter=lambda album: {"full": [2024, 2024], "cut": [2024], "other-year": [2023]}[album["id"]],
        )

        self.assertEqual(len(groups), 1)
        self.assertEqual({album["id"] for album in groups[0]["similar_albums"]}, {"full", "cut"})

    def test_scan_album_consolidation_groups_keeps_share_suffix_variants_separate_from_plain_name(self):
        groups = scan_album_consolidation_groups(
            [
                {"id": "plain", "albumName": "2024-07 - Vacaciones París, Londres, Noruega"},
                {"id": "shared", "albumName": "2024-07 - Vacaciones París, Londres, Noruega (Shar"},
            ],
            asset_years_getter=lambda _album: [2024, 2024],
        )

        self.assertEqual(groups, [])

    def test_scan_album_consolidation_groups_keeps_x_share_suffix_separate_from_plain_name(self):
        groups = scan_album_consolidation_groups(
            [
                {"id": "plain", "albumName": "2017 - Verano con Yraly"},
                {"id": "shared", "albumName": "2017 - Verano con Yraly X"},
            ],
            asset_years_getter=lambda _album: [2017, 2017],
        )

        self.assertEqual(groups, [])

    def test_scan_album_consolidation_groups_merges_truncated_share_suffix_variants(self):
        groups = scan_album_consolidation_groups(
            [
                {"id": "cut", "albumName": "2024-07 - Vacaciones París, Londres, Noruega (Shar"},
                {"id": "full", "albumName": "2024-07 - Vacaciones París, Londres, Noruega (Shared)"},
            ],
            asset_years_getter=lambda _album: [2024, 2024],
        )

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["keeper_album"]["id"], "full")

    def test_confirm_continue_skips_prompt_when_confirmation_is_disabled(self):
        with (
            patch.object(GV, "ARGS", {"request-user-confirmation": False}),
            patch.object(GV, "LOGGER", MagicMock()),
        ):
            self.assertTrue(confirm_continue())

    def test_confirm_continue_force_prompt_overrides_disabled_confirmation(self):
        fake_stdin = MagicMock()
        fake_stdin.isatty.return_value = True
        with (
            patch.object(GV, "ARGS", {"request-user-confirmation": False}),
            patch.object(GV, "LOGGER", MagicMock()),
            patch("Utils.GeneralUtils.sys.stdin", fake_stdin),
            patch("builtins.input", return_value="yes"),
        ):
            self.assertTrue(confirm_continue(force_prompt=True))

    def test_has_any_filter_treats_filter_by_type_all_as_no_filter(self):
        with patch.object(GV, "ARGS", {"filter-by-type": "all"}):
            self.assertFalse(has_any_filter())

        with patch.object(GV, "ARGS", {"filter-by-type": "photos"}):
            self.assertTrue(has_any_filter())


if __name__ == "__main__":
    unittest.main()
