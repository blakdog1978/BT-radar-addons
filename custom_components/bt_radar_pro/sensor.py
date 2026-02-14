"""Sensor platform for Bluetooth Radar Pro."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_NAME, ATTR_RSSI, ATTR_SOURCE
from .coordinator import BluetoothRadarCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator: BluetoothRadarCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        BluetoothRadarRSSISensor(coordinator, entry),
        BluetoothRadarSourceSensor(coordinator, entry)
    ])

class BluetoothRadarRSSISensor(CoordinatorEntity, SensorEntity):
    """Sensor showing the best RSSI strength."""

    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_native_unit_of_measurement = "dBm"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_name = f"{entry.data[CONF_NAME]} Signal Strength"
        self._attr_unique_id = f"{entry.entry_id}_rssi"

    @property
    def native_value(self):
        return self.coordinator.data.get("best_rssi")

class BluetoothRadarSourceSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing the closest proxy (source)."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_name = f"{entry.data[CONF_NAME]} Closest Proxy"
        self._attr_unique_id = f"{entry.entry_id}_source"
        self._attr_icon = "mdi:radar"

    @property
    def native_value(self):
        return self.coordinator.data.get("best_source")
