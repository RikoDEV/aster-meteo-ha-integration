"""Data update coordinator - one per configured station."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import AsterApiError, AsterClient
from .const import (
    CONF_MAX_AGE,
    CONF_SCAN_INTERVAL,
    CONF_STATION_ID,
    DEFAULT_MAX_AGE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .parser import StationData

if TYPE_CHECKING:
    from . import AsterConfigEntry

_LOGGER = logging.getLogger(__name__)


class AsterCoordinator(DataUpdateCoordinator[StationData]):
    """Poll one station."""

    config_entry: AsterConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: AsterConfigEntry,
        subentry: ConfigSubentry,
        client: AsterClient,
    ) -> None:
        """Initialize the coordinator."""
        self.station_id: str = str(subentry.data[CONF_STATION_ID])
        self.station_name: str = subentry.title
        self.subentry_id = subentry.subentry_id
        self.max_age = timedelta(hours=subentry.data.get(CONF_MAX_AGE, DEFAULT_MAX_AGE))
        self._client = client
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} station {self.station_id}",
            update_interval=timedelta(
                minutes=subentry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )

    async def _async_update_data(self) -> StationData:
        """Fetch the latest reading."""
        try:
            return await self._client.async_get_station(self.station_id)
        except AsterApiError as err:
            raise UpdateFailed(str(err)) from err

    @property
    def is_stale(self) -> bool:
        """Return True when the station has stopped reporting."""
        if self.data is None or self.data.updated is None:
            return True
        return dt_util.utcnow() - self.data.updated > self.max_age
