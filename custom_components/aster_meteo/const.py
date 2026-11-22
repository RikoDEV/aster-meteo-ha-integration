"""Constants for the A-Ster.pl Meteo integration."""

from __future__ import annotations

DOMAIN = "aster_meteo"

# The ASTERGate network is operated by IUNG-PIB (Puławy). Station readings are
# published as a JavaScript-object-like document at ``data2.php?s=<station id>``.
DEFAULT_BASE_URL = "http://meteor.iung.pulawy.pl"
DATA_PATH = "/data2.php"

CONF_BASE_URL = "base_url"
CONF_STATION_ID = "station_id"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_MAX_AGE = "max_age"

DEFAULT_SCAN_INTERVAL = 10  # minutes
DEFAULT_MAX_AGE = 6  # hours - older readings make the entities unavailable

SUBENTRY_STATION = "station"

MANUFACTURER = "IUNG-PIB Puławy (A-Ster)"
MODEL = "A-Ster meteo station"
