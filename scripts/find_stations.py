#!/usr/bin/env python3
"""List A-Ster stations that currently report data.

The network has no public station directory (the portal needs a login), so this
helper probes a range of station IDs and prints the ones that answer with a
fresh measurement. Use it to find the ID of the station nearest to you, then add
that ID in Home Assistant.

    python scripts/find_stations.py                 # IDs 1-500, fresh data only
    python scripts/find_stations.py 400 440 --all   # also show stale stations

Be considerate: the default probes ~500 IDs with 4 parallel connections.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import importlib.util
from pathlib import Path
import sys
import urllib.request

PARSER = Path(__file__).resolve().parent.parent / "custom_components" / "aster_meteo" / "parser.py"
spec = importlib.util.spec_from_file_location("aster_parser", PARSER)
parser = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = parser
spec.loader.exec_module(parser)

BASE_URL = "http://meteor.iung.pulawy.pl/data2.php?s={}"


def probe(station_id: int):
    try:
        with urllib.request.urlopen(BASE_URL.format(station_id), timeout=20) as response:
            text = response.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    data = parser.parse_station(str(station_id), text)
    return data if data.has_readings or data.updated else None


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    cli.add_argument("first", nargs="?", type=int, default=1)
    cli.add_argument("last", nargs="?", type=int, default=500)
    cli.add_argument("--all", action="store_true", help="include stations without fresh data")
    cli.add_argument("--max-age", type=int, default=6, help="hours considered fresh")
    args = cli.parse_args()

    now = datetime.now().astimezone()
    print(f"{'ID':>5}  {'last measurement':<17}  {'temp':>6}  {'humid':>6}  {'wind m/s':>8}  pressure")
    with ThreadPoolExecutor(max_workers=4) as pool:
        for station_id, data in zip(
            range(args.first, args.last + 1),
            pool.map(probe, range(args.first, args.last + 1)),
        ):
            if data is None:
                continue
            fresh = data.updated is not None and now - data.updated <= timedelta(hours=args.max_age)
            if not fresh and not args.all:
                continue

            def fmt(key: str) -> str:
                value = data.number(key)
                return "-" if value is None else f"{value:g}"

            stamp = data.updated.strftime("%Y-%m-%d %H:%M") if data.updated else "never"
            print(
                f"{station_id:>5}  {stamp:<17}  {fmt('temperatureInt'):>6}  "
                f"{fmt('humidityInt'):>6}  {fmt('windSpeed'):>8}  {fmt('pressInt')}"
            )


if __name__ == "__main__":
    main()
