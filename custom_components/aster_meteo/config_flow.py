"""Config flow: the server entry plus one subentry per meteo station."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryData,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AsterClient, AsterConnectionError, AsterNoDataError
from .const import (
    CONF_BASE_URL,
    CONF_MAX_AGE,
    CONF_SCAN_INTERVAL,
    CONF_STATION_ID,
    DEFAULT_BASE_URL,
    DEFAULT_MAX_AGE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SUBENTRY_STATION,
)


def _station_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Return the form schema shared by the first and the following stations."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_STATION_ID, default=defaults.get(CONF_STATION_ID, vol.UNDEFINED)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=99999, step=1, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Optional(
                CONF_NAME, default=defaults.get(CONF_NAME, vol.UNDEFINED)
            ): selector.TextSelector(),
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=5,
                    max=120,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="min",
                )
            ),
            vol.Required(
                CONF_MAX_AGE, default=defaults.get(CONF_MAX_AGE, DEFAULT_MAX_AGE)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=168,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="h",
                )
            ),
        }
    )


async def _validate_station(hass, base_url: str, station_id: str) -> str | None:
    """Return an error key when the station cannot be used, else ``None``."""
    client = AsterClient(async_get_clientsession(hass), base_url)
    try:
        await client.async_get_station(station_id)
    except AsterConnectionError:
        return "cannot_connect"
    except AsterNoDataError:
        return "no_data"
    return None


def _station_data(user_input: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
    """Normalise the submitted form into (station id, subentry data, title)."""
    station_id = str(int(user_input[CONF_STATION_ID]))
    name = (user_input.get(CONF_NAME) or "").strip() or f"A-Ster {station_id}"
    data = {
        CONF_STATION_ID: station_id,
        CONF_NAME: name,
        CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
        CONF_MAX_AGE: int(user_input[CONF_MAX_AGE]),
    }
    return station_id, data, name


class AsterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create the server entry together with the first station."""

    VERSION = 1
    MINOR_VERSION = 2

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Stations are subentries of the server entry."""
        return {SUBENTRY_STATION: StationSubentryFlow}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the first station."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}
        if user_input is not None:
            station_id, data, name = _station_data(user_input)
            error = await _validate_station(self.hass, DEFAULT_BASE_URL, station_id)
            if error is None:
                return self.async_create_entry(
                    title="A-Ster.pl Meteo",
                    data={CONF_BASE_URL: DEFAULT_BASE_URL},
                    subentries=[
                        ConfigSubentryData(
                            data=data,
                            subentry_type=SUBENTRY_STATION,
                            title=name,
                            unique_id=station_id,
                        )
                    ],
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                _station_schema(), user_input
            ),
            errors=errors,
        )


class StationSubentryFlow(ConfigSubentryFlow):
    """Add or reconfigure a meteo station."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Add a station."""
        return await self._async_station_step("user", user_input)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Reconfigure an existing station."""
        return await self._async_station_step("reconfigure", user_input)

    async def _async_station_step(
        self, step_id: str, user_input: dict[str, Any] | None
    ) -> SubentryFlowResult:
        entry = self._get_entry()
        existing = self._get_reconfigure_subentry() if step_id == "reconfigure" else None
        errors: dict[str, str] = {}

        if user_input is not None:
            station_id, data, name = _station_data(user_input)
            if any(
                sub.unique_id == station_id
                and (existing is None or sub.subentry_id != existing.subentry_id)
                for sub in entry.subentries.values()
            ):
                errors["base"] = "already_configured"
            else:
                error = await _validate_station(
                    self.hass, entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL), station_id
                )
                if error is None:
                    if existing is not None:
                        return self.async_update_and_abort(
                            entry,
                            existing,
                            unique_id=station_id,
                            title=name,
                            data=data,
                        )
                    return self.async_create_entry(
                        title=name, data=data, unique_id=station_id
                    )
                errors["base"] = error

        defaults = user_input or (dict(existing.data) if existing is not None else None)
        return self.async_show_form(
            step_id=step_id,
            data_schema=self.add_suggested_values_to_schema(
                _station_schema(), defaults
            ),
            errors=errors,
        )
