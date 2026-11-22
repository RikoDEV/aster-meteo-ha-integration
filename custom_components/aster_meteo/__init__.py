"""The A-Ster.pl Meteo integration.

One config entry represents the A-Ster server. Every meteo station is a
``station`` subentry of that entry, so any number of stations can be added from
the integration page ("Add meteo station").
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AsterClient
from .const import CONF_BASE_URL, DEFAULT_BASE_URL, SUBENTRY_STATION
from .coordinator import AsterCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.WEATHER]


@dataclass
class AsterRuntimeData:
    """Runtime data of a config entry."""

    client: AsterClient
    coordinators: dict[str, AsterCoordinator]  # subentry_id -> coordinator


type AsterConfigEntry = ConfigEntry[AsterRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: AsterConfigEntry) -> bool:
    """Set up the integration from a config entry."""
    client = AsterClient(
        async_get_clientsession(hass),
        entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL),
    )

    coordinators: dict[str, AsterCoordinator] = {}
    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type != SUBENTRY_STATION:
            continue
        coordinator = AsterCoordinator(hass, entry, subentry, client)
        # A failing station must not prevent the other stations from loading, so
        # use async_refresh() (which never raises) instead of the first-refresh
        # helper. Its entities simply stay unavailable until data arrives.
        await coordinator.async_refresh()
        coordinators[subentry_id] = coordinator

    entry.runtime_data = AsterRuntimeData(client=client, coordinators=coordinators)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_change))
    return True


async def _async_reload_on_change(hass: HomeAssistant, entry: AsterConfigEntry) -> None:
    """Reload when a station is added, changed or removed."""
    hass.config_entries.async_schedule_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: AsterConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
