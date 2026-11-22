"""Weather entity (current conditions only) for A-Ster meteo stations."""

from __future__ import annotations

import math

from homeassistant.components.weather import WeatherEntity
from homeassistant.const import (
    UnitOfLength,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import AsterConfigEntry
from .coordinator import AsterCoordinator
from .sensor import station_device_info

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AsterConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create one weather entity per station."""
    for subentry_id, coordinator in entry.runtime_data.coordinators.items():
        async_add_entities([AsterWeather(coordinator)], config_subentry_id=subentry_id)


class AsterWeather(CoordinatorEntity[AsterCoordinator], WeatherEntity):
    """Current conditions of a station.

    The stations only measure, they do not forecast, so there is no forecast
    support. The condition is an estimate derived from the readings.
    """

    _attr_has_entity_name = True
    _attr_name = None
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_pressure_unit = UnitOfPressure.HPA
    _attr_native_wind_speed_unit = UnitOfSpeed.METERS_PER_SECOND
    _attr_native_precipitation_unit = UnitOfLength.MILLIMETERS

    def __init__(self, coordinator: AsterCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.subentry_id}_weather"
        self._attr_device_info = station_device_info(coordinator)

    @property
    def available(self) -> bool:
        """Unavailable while the station is silent or has no temperature."""
        return (
            super().available
            and not self.coordinator.is_stale
            and self.coordinator.data.number("temperatureInt") is not None
        )

    @property
    def native_temperature(self) -> float | None:
        """Return the air temperature."""
        return self.coordinator.data.number("temperatureInt")

    @property
    def humidity(self) -> float | None:
        """Return the relative humidity."""
        return self.coordinator.data.number("humidityInt")

    @property
    def native_pressure(self) -> float | None:
        """Return the pressure (only some stations have a barometer)."""
        return self.coordinator.data.number("pressInt")

    @property
    def native_wind_speed(self) -> float | None:
        """Return the wind speed in m/s."""
        return self.coordinator.data.number("windSpeed")

    @property
    def wind_bearing(self) -> float | None:
        """Return the wind direction."""
        return self.coordinator.data.number("windDir")

    @property
    def native_dew_point(self) -> float | None:
        """Return the dew point (Magnus formula)."""
        temperature, humidity = self.native_temperature, self.humidity
        if temperature is None or humidity is None or humidity <= 0:
            return None
        a, b = 17.62, 243.12
        gamma = math.log(humidity / 100) + a * temperature / (b + temperature)
        return round(b * gamma / (a - gamma), 1)

    @property
    def condition(self) -> str | None:
        """Estimate the condition from the readings."""
        data = self.coordinator.data
        precipitation = data.number("Op_Typ")
        humidity = data.number("humidityInt")
        wind = data.number("windSpeed")
        sunshine = data.number("irr_durInt")

        if precipitation:
            return "hail" if int(precipitation) == 90 else "rainy"
        if humidity is not None and humidity >= 97 and (wind is None or wind < 2):
            return "fog"
        if wind is not None and wind >= 11:
            return "windy"

        sun = self.hass.states.get("sun.sun")
        is_day = sun is None or sun.state == "above_horizon"
        if is_day:
            if sunshine:
                return "sunny"
            return "partlycloudy" if humidity is not None and humidity < 70 else "cloudy"
        return "clear-night" if humidity is not None and humidity < 75 else "cloudy"
