from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NedCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coord: NedCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        NedCurrentSlotSensor(coord, entry),
        NedForecastMinSensor(coord, entry),
        NedForecastBestStartSensor(coord, entry),
        NedForecastBestEndSensor(coord, entry),
    ]
    async_add_entities(entities)


class NedBase(CoordinatorEntity[NedCoordinator], SensorEntity):
    """Base sensor with common device info and naming."""

    _attr_has_entity_name = True  # allow nice names under the device

    def __init__(self, coordinator: NedCoordinator, entry: ConfigEntry, name: str, unique_suffix: str, object_id: str):
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"

        # Hint HA for the entity_id slug (not guaranteed if already exists)
        self._attr_suggested_object_id = object_id  # e.g., "ned_ef_current_slot"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="NED CO2",
            manufacturer="NED",
            model="Electricity Mix (Type 27)",
        )


class NedCurrentSlotSensor(NedBase):
    """State = emission factor (kg/kWh) for the current slot."""

    _attr_native_unit_of_measurement = "kg/kWh"
    _attr_state_class = "measurement"

    def __init__(self, c: NedCoordinator, e: ConfigEntry):
        super().__init__(c, e, name="NED EF (current slot)", unique_suffix="current_slot", object_id="ned_ef_current_slot")

    @property
    def native_value(self):
        rows = (self.coordinator.data or {}).get("current", {}).get("hydra:member", [])
        hit = self.coordinator._match_current_slot(rows)
        return hit.get("emissionfactor") if hit else None

    @property
    def extra_state_attributes(self):
        rows = (self.coordinator.data or {}).get("current", {}).get("hydra:member", [])
        hit = self.coordinator._match_current_slot(rows)
        if not hit:
            return {}
        return {
            "slot_start_utc": hit.get("validfrom"),
            "slot_end_utc": hit.get("validto"),
        }


class NedForecastMinSensor(NedBase):
    """State = minimum forecast emission factor in the window."""

    _attr_native_unit_of_measurement = "kg/kWh"

    def __init__(self, c: NedCoordinator, e: ConfigEntry):
        super().__init__(c, e, name="NED EF (forecast min)", unique_suffix="forecast_min", object_id="ned_ef_forecast_min")

    @property
    def native_value(self):
        rows = (self.coordinator.data or {}).get("forecast", {}).get("hydra:member", [])
        best = self.coordinator._min_slot(rows)
        return best.get("emissionfactor") if best else None


class NedForecastBestStartSensor(NedBase):
    """Timestamp for start of greenest forecast slot."""

    _attr_device_class = "timestamp"

    def __init__(self, c: NedCoordinator, e: ConfigEntry):
        super().__init__(c, e, name="NED EF forecast best start", unique_suffix="forecast_best_start", object_id="ned_ef_forecast_best_start")

    @property
    def native_value(self):
        rows = (self.coordinator.data or {}).get("forecast", {}).get("hydra:member", [])
        best = self.coordinator._min_slot(rows)
        return best.get("validfrom") if best else None


class NedForecastBestEndSensor(NedBase):
    """Timestamp for end of greenest forecast slot."""

    _attr_device_class = "timestamp"

    def __init__(self, c: NedCoordinator, e: ConfigEntry):
        super().__init__(c, e, name="NED EF forecast best end", unique_suffix="forecast_best_end", object_id="ned_ef_forecast_best_end")

    @property
    def native_value(self):
        rows = (self.coordinator.data or {}).get("forecast", {}).get("hydra:member", [])
        best = self.coordinator._min_slot(rows)
        return best.get("validto") if best else None
