"""Device Tracker platform for Bluetooth Radar Pro."""
from __future__ import annotations

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_NAME
from .coordinator import BluetoothRadarCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the device tracker platform."""
    coordinator: BluetoothRadarCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([BluetoothRadarTracker(coordinator, entry)])

class BluetoothRadarTracker(CoordinatorEntity, TrackerEntity):
    """Device tracker entity."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_name = entry.data[CONF_NAME]
        self._attr_unique_id = f"{entry.entry_id}_tracker"

    @property
    def source_type(self) -> SourceType:
        """Return the source type."""
        return SourceType.BLUETOOTH

    @property
    def location_name(self) -> str | None:
        """Return the location name (Room/Area)."""
        # Logic to map 'best_source' (proxy) to 'Area' needs to happen here or in coordinator
        # For now, we return the proxy name as location, or 'home' if present.
        
        if not self.coordinator.data.get("is_home"):
            return "not_home"
            
        # In a real calibration scenario, this would return "Kitchen", "Living Room", etc.
        # based on the triangulation logic.
        return self.coordinator.data.get("best_source") or "home"

    @property
    def icon(self):
        return "mdi:bluetooth-connect"
