from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.components import bluetooth
from .coordinator import BluetoothRadarCoordinator
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Configura l'integrazione."""
    coordinator = BluetoothRadarCoordinator(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    @callback
    def _handle_bt_event(service_info, change):
        coordinator.update_device(
            service_info.address, 
            service_info.rssi, 
            service_info.source
        )

    # Registra il callback nativo
    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass, _handle_bt_event, 
            bluetooth.BluetoothScanningFilters(connectable=False),
            bluetooth.BluetoothScanningMode.ACTIVE
        )
    )
    return True
