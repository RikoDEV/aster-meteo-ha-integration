"""The A-Ster.pl Meteo integration.

One config entry represents the A-Ster server. Every meteo station is a
``station`` subentry of that entry, so any number of stations can be added from
the integration page ("Add meteo station").
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AsterClient
from .const import CONF_BASE_URL, CONF_STATION_ID, DEFAULT_BASE_URL, DOMAIN, SUBENTRY_STATION
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
    _async_prune_stale_devices(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_change))
    return True


async def _async_reload_on_change(hass: HomeAssistant, entry: AsterConfigEntry) -> None:
    """Reload when a station is added, changed or removed."""
    hass.config_entries.async_schedule_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: AsterConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


def _active_station_ids(entry: AsterConfigEntry) -> set[str]:
    """Return the IDs of the stations that are currently configured."""
    return {
        str(subentry.data[CONF_STATION_ID])
        for subentry in entry.subentries.values()
        if subentry.subentry_type == SUBENTRY_STATION
    }


def _device_station_ids(device: dr.DeviceEntry) -> set[str]:
    return {ident[1] for ident in device.identifiers if ident[0] == DOMAIN}


@callback
def _async_prune_stale_devices(hass: HomeAssistant, entry: AsterConfigEntry) -> None:
    """Remove devices of stations that are no longer configured.

    Reconfiguring a station to another ID leaves the device (and entities) of
    the old ID behind; they would stay unavailable forever.
    """
    active = _active_station_ids(entry)
    registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(registry, entry.entry_id):
        stations = _device_station_ids(device)
        if stations and not stations & active:
            registry.async_remove_device(device.id)


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: AsterConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Allow deleting a device from the UI unless its station is still configured."""
    return not _device_station_ids(device_entry) & _active_station_ids(entry)
