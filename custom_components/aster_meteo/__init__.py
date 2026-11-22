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
from homeassistant.helpers import device_registry as dr, entity_registry as er
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


def _active_keys(entry: AsterConfigEntry) -> set[str]:
    """Return the keys (subentry IDs) of the configured stations.

    Devices and entities are keyed by the subentry ID, not by the station
    number, so reconfiguring a station to another number edits the same device
    instead of creating a second one.
    """
    return {
        subentry_id
        for subentry_id, subentry in entry.subentries.items()
        if subentry.subentry_type == SUBENTRY_STATION
    }


def _device_keys(device: dr.DeviceEntry) -> set[str]:
    return {ident[1] for ident in device.identifiers if ident[0] == DOMAIN}


async def async_migrate_entry(hass: HomeAssistant, entry: AsterConfigEntry) -> bool:
    """Migrate 1.0 -> 1.2: key devices and entities by subentry ID."""
    if entry.version == 1 and entry.minor_version < 2:
        device_registry = dr.async_get(hass)
        for subentry_id, subentry in entry.subentries.items():
            if subentry.subentry_type != SUBENTRY_STATION:
                continue
            station = str(subentry.data[CONF_STATION_ID])
            device = device_registry.async_get_device(identifiers={(DOMAIN, station)})
            if device is not None and entry.entry_id in device.config_entries:
                device_registry.async_update_device(
                    device.id, new_identifiers={(DOMAIN, subentry_id)}
                )

        @callback
        def _new_unique_id(reg_entry: er.RegistryEntry) -> dict[str, str] | None:
            subentry = entry.subentries.get(reg_entry.config_subentry_id or "")
            if subentry is None:
                return None
            prefix = f"{subentry.data[CONF_STATION_ID]}_"
            if reg_entry.unique_id.startswith(prefix):
                suffix = reg_entry.unique_id[len(prefix) :]
                return {"new_unique_id": f"{reg_entry.config_subentry_id}_{suffix}"}
            return None  # entity of a station this subentry used to point to

        await er.async_migrate_entries(hass, entry.entry_id, _new_unique_id)
        hass.config_entries.async_update_entry(entry, minor_version=2)
    return True


@callback
def _async_prune_stale_devices(hass: HomeAssistant, entry: AsterConfigEntry) -> None:
    """Remove devices that do not belong to a configured station any more.

    That covers leftovers from versions that keyed devices by station number.
    """
    active = _active_keys(entry)
    registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(registry, entry.entry_id):
        keys = _device_keys(device)
        if keys and not keys & active:
            registry.async_remove_device(device.id)


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: AsterConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Let the user delete a station from its device page.

    Deleting the device also removes the station (the subentry); otherwise the
    next reload would simply create the device again. The subentry is removed on
    the next loop iteration, after Home Assistant has finished detaching the
    device from this entry.
    """
    keys = _device_keys(device_entry) & _active_keys(entry)

    def _remove_station_subentries() -> None:
        for key in keys:
            hass.config_entries.async_remove_subentry(entry, key)

    hass.loop.call_soon(_remove_station_subentries)
    return True
