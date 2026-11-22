"""Sensors for A-Ster meteo stations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    DEGREE,
    PERCENTAGE,
    EntityCategory,
    UnitOfLength,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import AsterConfigEntry
from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import AsterCoordinator

PARALLEL_UPDATES = 0

# ``Op_Typ`` code -> state. 40 and 90 are the values observed on the stations,
# anything else is reported as "other".
PRECIPITATION_TYPES = {0: "none", 40: "rain", 90: "hail"}


def _precipitation_type(value: float | str) -> str:
    try:
        return PRECIPITATION_TYPES.get(int(float(value)), "other")
    except (TypeError, ValueError):
        return "other"


@dataclass(frozen=True, kw_only=True)
class AsterSensorDescription(SensorEntityDescription):
    """Describes a reading of the station payload."""

    api_key: str
    value_fn: Callable[[float | str], StateType] | None = None


def _temperature(key: str, api_key: str, **kwargs) -> AsterSensorDescription:
    return AsterSensorDescription(
        key=key,
        api_key=api_key,
        translation_key=key,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        **kwargs,
    )


def _soil(depth: int) -> AsterSensorDescription:
    return AsterSensorDescription(
        key=f"soil_moisture_{depth}cm",
        api_key=f"soil{depth}",
        translation_key=f"soil_moisture_{depth}cm",
        device_class=SensorDeviceClass.MOISTURE,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    )


SENSORS: tuple[AsterSensorDescription, ...] = (
    _temperature("air_temperature", "temperatureInt"),
    AsterSensorDescription(
        key="humidity",
        api_key="humidityInt",
        translation_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    AsterSensorDescription(
        key="pressure",
        api_key="pressInt",
        translation_key="pressure",
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        native_unit_of_measurement=UnitOfPressure.HPA,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    AsterSensorDescription(
        key="wind_speed",
        api_key="windSpeed",
        translation_key="wind_speed",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    AsterSensorDescription(
        key="wind_direction",
        api_key="windDir",
        translation_key="wind_direction",
        native_unit_of_measurement=DEGREE,
        state_class=SensorStateClass.MEASUREMENT_ANGLE,
        icon="mdi:compass",
        suggested_display_precision=0,
    ),
    AsterSensorDescription(
        key="rain_today",
        api_key="rainT",
        translation_key="rain_today",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
    ),
    AsterSensorDescription(
        key="rain_yesterday",
        api_key="rainY",
        translation_key="rain_yesterday",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    AsterSensorDescription(
        key="precipitation_type",
        api_key="Op_Typ",
        translation_key="precipitation_type",
        device_class=SensorDeviceClass.ENUM,
        options=["none", "rain", "hail", "other"],
        icon="mdi:weather-pouring",
        value_fn=_precipitation_type,
    ),
    _temperature("ground_temperature", "t5Int"),
    _temperature("soil_temperature_10cm", "tg10Int"),
    AsterSensorDescription(
        key="leaf_wetness",
        api_key="leafInt",
        translation_key="leaf_wetness",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:leaf",
        suggested_display_precision=1,
    ),
    AsterSensorDescription(
        key="sunshine_duration",
        api_key="irr_durInt",
        translation_key="sunshine_duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-sunny",
    ),
    AsterSensorDescription(
        key="pm25",
        api_key="pm2Int",
        translation_key="pm25",
        device_class=SensorDeviceClass.PM25,
        native_unit_of_measurement="µg/m³",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AsterSensorDescription(
        key="pm10",
        api_key="pm10Int",
        translation_key="pm10",
        device_class=SensorDeviceClass.PM10,
        native_unit_of_measurement="µg/m³",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    *(_soil(depth) for depth in (10, 20, 30, 40, 60, 100)),
)


def station_device_info(coordinator: AsterCoordinator) -> DeviceInfo:
    """Return the device of a station."""
    return DeviceInfo(
        identifiers={(DOMAIN, coordinator.subentry_id)},
        name=coordinator.station_name,
        manufacturer=MANUFACTURER,
        model=MODEL,
        serial_number=coordinator.station_id,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AsterConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create sensors for every configured station.

    Stations differ a lot (many have no pressure or soil probes), so a sensor is
    only created once the station actually reports that reading.
    """
    for subentry_id, coordinator in entry.runtime_data.coordinators.items():
        known: set[str] = set()

        @callback
        def _add_missing(
            coordinator: AsterCoordinator = coordinator,
            subentry_id: str = subentry_id,
            known: set[str] = known,
        ) -> None:
            if coordinator.data is None:
                return
            new: list[SensorEntity] = []
            if "last_update" not in known:
                known.add("last_update")
                new.append(AsterLastUpdateSensor(coordinator))
            for description in SENSORS:
                if description.key in known:
                    continue
                if coordinator.data.number(description.api_key) is None:
                    continue
                known.add(description.key)
                new.append(AsterSensor(coordinator, description))
            if new:
                async_add_entities(new, config_subentry_id=subentry_id)

        entry.async_on_unload(coordinator.async_add_listener(_add_missing))
        _add_missing()


class AsterBaseEntity(CoordinatorEntity[AsterCoordinator]):
    """Shared behaviour of the station entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AsterCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_device_info = station_device_info(coordinator)

    @property
    def available(self) -> bool:
        """Entities are unavailable while the station is silent."""
        return super().available and not self.coordinator.is_stale


class AsterSensor(AsterBaseEntity, SensorEntity):
    """A numeric (or enum) reading of a station."""

    entity_description: AsterSensorDescription

    def __init__(
        self, coordinator: AsterCoordinator, description: AsterSensorDescription
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.subentry_id}_{description.api_key}"

    @property
    def available(self) -> bool:
        """A reading that disappeared from the payload is unavailable."""
        return (
            super().available
            and self.coordinator.data.number(self.entity_description.api_key)
            is not None
        )

    @property
    def native_value(self) -> StateType:
        """Return the reading."""
        value = self.coordinator.data.number(self.entity_description.api_key)
        if value is None:
            return None
        if self.entity_description.value_fn is not None:
            return self.entity_description.value_fn(value)
        return value


class AsterLastUpdateSensor(AsterBaseEntity, SensorEntity):
    """Time of the station's last measurement."""

    _attr_translation_key = "last_update"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: AsterCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.subentry_id}_last_update"

    @property
    def available(self) -> bool:
        """Stay available when the station is stale - that is the point."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data.updated is not None
        )

    @property
    def native_value(self) -> datetime | None:
        """Return the timestamp of the last measurement."""
        return self.coordinator.data.updated
