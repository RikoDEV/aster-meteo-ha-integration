"""Parser for the payload returned by the A-Ster ``data2.php`` endpoint.

The endpoint does not return JSON. It returns a JavaScript object literal with
a handful of scalar values (current readings) and a few nested chart series.
Only the top-level scalars are interesting, so the nested blocks are blanked out
before the key/value pairs are extracted.

This module deliberately has no Home Assistant dependency so it can be tested
(and reused) on its own.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import re
from zoneinfo import ZoneInfo


def _station_tz() -> ZoneInfo:
    """Return the (lazily loaded) time zone the stations report in."""
    return ZoneInfo("Europe/Warsaw")


_PAIR = re.compile(
    r"(?P<key>[A-Za-z_]\w*)\s*:\s*"
    r"(?P<value>\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'|[^,}\s]+)"
)


def _flatten(text: str) -> str:
    """Return the top-level part of the object, nested blocks become ``null``."""
    out: list[str] = []
    depth = 0
    quote = ""
    escaped = False

    for char in text:
        if quote:
            if depth <= 1:
                out.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            continue
        if char in "\"'":
            quote = char
            if depth <= 1:
                out.append(char)
            continue
        if char in "{[":
            depth += 1
            if depth == 2:
                out.append("null")
            continue
        if char in "}]":
            depth -= 1
            continue
        if depth <= 1:
            out.append(char)

    return "".join(out)


def _convert(raw: str) -> float | str | None:
    """Convert a raw token to a number, string or ``None``."""
    value = raw.strip()
    if value[:1] in "\"'" and value[-1:] == value[:1]:
        value = value[1:-1]
    value = value.strip()
    if value in ("", "null", "undefined", "NaN"):
        return None
    try:
        return float(value)
    except ValueError:
        return value


def parse_values(text: str) -> dict[str, float | str | None]:
    """Extract the top-level key/value pairs from a ``data2.php`` response."""
    values: dict[str, float | str | None] = {}
    for match in _PAIR.finditer(_flatten(text)):
        values[match.group("key")] = _convert(match.group("value"))
    return values


def parse_timestamp(value: object) -> datetime | None:
    """Parse the ``data`` field (local Polish time) into an aware datetime."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    if parsed.year < 2000:  # stations without data report 1970-01-01
        return None
    return parsed.replace(tzinfo=_station_tz())


@dataclass(slots=True)
class StationData:
    """Latest reading of a single station."""

    station_id: str
    updated: datetime | None
    values: dict[str, float | str | None] = field(default_factory=dict)

    def number(self, key: str) -> float | None:
        """Return a numeric reading or ``None`` when it is missing."""
        value = self.values.get(key)
        return value if isinstance(value, float) else None

    @property
    def has_readings(self) -> bool:
        """Return True when at least one numeric reading is present."""
        return any(isinstance(v, float) for k, v in self.values.items() if k != "data")


def parse_station(station_id: str, text: str) -> StationData:
    """Parse a full ``data2.php`` response."""
    values = parse_values(text)
    return StationData(
        station_id=station_id,
        updated=parse_timestamp(values.get("data")),
        values=values,
    )
