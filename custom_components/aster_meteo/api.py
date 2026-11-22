"""Small async client for the A-Ster (ASTERGate) station data endpoint."""

from __future__ import annotations

import asyncio

import aiohttp

from .const import DATA_PATH
from .parser import StationData, parse_station


class AsterApiError(Exception):
    """Base error of the A-Ster client."""


class AsterConnectionError(AsterApiError):
    """The endpoint could not be reached."""


class AsterNoDataError(AsterApiError):
    """The station exists but did not return any readings."""


class AsterClient:
    """Fetch readings for stations of one A-Ster server."""

    def __init__(self, session: aiohttp.ClientSession, base_url: str) -> None:
        """Initialize the client."""
        self._session = session
        self._base_url = base_url.rstrip("/")

    async def async_get_station(self, station_id: str) -> StationData:
        """Return the latest reading of ``station_id``."""
        url = f"{self._base_url}{DATA_PATH}"
        try:
            async with asyncio.timeout(30):
                response = await self._session.get(url, params={"s": station_id})
                response.raise_for_status()
                text = await response.text(errors="replace")
        except (aiohttp.ClientError, TimeoutError) as err:
            raise AsterConnectionError(
                f"Cannot fetch station {station_id}: {err}"
            ) from err

        data = parse_station(station_id, text)
        if not data.has_readings:
            raise AsterNoDataError(f"Station {station_id} returned no readings")
        return data
