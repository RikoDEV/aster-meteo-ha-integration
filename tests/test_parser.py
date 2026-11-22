"""Tests for the payload parser (stdlib only - no Home Assistant needed).

Run with:  python -m unittest discover -s tests -v
"""

from __future__ import annotations

from datetime import datetime
import importlib.util
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"

# Load parser.py directly: importing the package would import Home Assistant.
_spec = importlib.util.spec_from_file_location(
    "aster_parser", ROOT / "custom_components" / "aster_meteo" / "parser.py"
)
parser = importlib.util.module_from_spec(_spec)
# dataclasses(slots=True) looks the module up in sys.modules while it is being created
sys.modules[_spec.name] = parser
_spec.loader.exec_module(parser)


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8", errors="replace")


class ParserTest(unittest.TestCase):
    def test_live_station(self) -> None:
        data = parser.parse_station("428", fixture("station_428.txt"))
        self.assertEqual(
            data.updated,
            datetime(2026, 11, 22, 15, 20, tzinfo=ZoneInfo("Europe/Warsaw")),
        )
        self.assertEqual(data.number("temperatureInt"), 3.0)
        self.assertEqual(data.number("humidityInt"), 77.01)
        self.assertEqual(data.number("windSpeed"), 5.64)
        self.assertEqual(data.number("windDir"), 292.78)
        self.assertEqual(data.number("rainT"), 0.7)
        self.assertEqual(data.number("soil100"), 33.0)
        self.assertTrue(data.has_readings)

    def test_empty_strings_are_missing(self) -> None:
        data = parser.parse_station("428", fixture("station_428.txt"))
        self.assertIsNone(data.number("pressInt"))
        self.assertIsNone(data.number("pm2Int"))

    def test_chart_series_are_not_scalars(self) -> None:
        data = parser.parse_station("428", fixture("station_428.txt"))
        # ``temperature`` / ``humidity`` hold chart series, not a reading.
        self.assertIsNone(data.values.get("temperature"))
        self.assertIsNone(data.values.get("humidity"))
        # keys inside the series must not leak to the top level
        self.assertNotIn("label", data.values)
        self.assertNotIn("color", data.values)

    def test_station_with_barometer(self) -> None:
        data = parser.parse_station("223", fixture("station_223_with_pressure.txt"))
        self.assertAlmostEqual(data.number("pressInt"), 992.51, places=2)

    def test_station_without_data(self) -> None:
        data = parser.parse_station("62", fixture("station_empty.txt"))
        self.assertIsNone(data.updated)  # 1970-01-01 is "never"
        self.assertIsNone(data.number("temperatureInt"))

    def test_quoted_numbers(self) -> None:
        values = parser.parse_values('{ a: "1.5", b: 2, c: "", d: "text, with comma" }')
        self.assertEqual(values["a"], 1.5)
        self.assertEqual(values["b"], 2.0)
        self.assertIsNone(values["c"])
        self.assertEqual(values["d"], "text, with comma")

    def test_garbage(self) -> None:
        self.assertEqual(parser.parse_values("<html>not a station</html>"), {})
        data = parser.parse_station("1", "<html>nope</html>")
        self.assertFalse(data.has_readings)


if __name__ == "__main__":
    unittest.main()
