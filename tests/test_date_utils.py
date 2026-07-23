import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from Utils.DateUtils import is_date_outside_calendar_range


class TestDateUtils(unittest.TestCase):
    def test_calendar_range_uses_local_date_shown_by_immich(self):
        # 22:30 UTC on 22 July is 00:30 on 23 July in Europe/Madrid.
        with patch("Utils.DateUtils.tzlocal.get_localzone", return_value=ZoneInfo("Europe/Madrid")):
            self.assertFalse(
                is_date_outside_calendar_range(
                    "2026-07-22T22:30:00.000Z",
                    date_from="2026-07-23T00:00:00.000Z",
                )
            )

    def test_calendar_range_excludes_prior_local_day(self):
        with patch("Utils.DateUtils.tzlocal.get_localzone", return_value=ZoneInfo("Europe/Madrid")):
            self.assertTrue(
                is_date_outside_calendar_range(
                    "2026-07-22T21:30:00.000Z",
                    date_from="2026-07-23T00:00:00.000Z",
                )
            )


if __name__ == "__main__":
    unittest.main()
