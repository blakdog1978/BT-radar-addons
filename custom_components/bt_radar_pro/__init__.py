import logging
from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Setup tramite YAML non necessario, ma supportato."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Configurazione dell'integrazione da interfaccia UI."""
    _LOGGER.info("🛰️ Avvio Radar Pro: Collegamento al flusso Bluetooth nativo...")

    @callback
    def _handle_bluetooth_event(
        service_info: BluetoothServiceInfoBleak, 
        change: bluetooth.BluetoothScanningMode
    ) -> None:
        """Questa funzione viene chiamata ogni volta che viene rilevato un segnale."""
        mac = service_info.address
        rssi = service_info.rssi
        scanner = service_info.source # Questo è il nome dello Shelly!

        # Calcolo distanza (Path Loss Model)
        dist = round(10**((-60 - rssi) / 22), 2)

        # Logghiamo i segnali forti per vedere se funziona
        if rssi > -70:
            _LOGGER.info(f"🎯 Segnale Intercettato: {mac} a {dist}m da {scanner}")

    # Registriamo il callback nel cuore di HA
    # In questo modo "scavalliamo" ogni blocco e leggiamo i dati alla fonte
    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            _handle_bluetooth_event,
            bluetooth.BluetoothScanningFilters(connectable=False),
            bluetooth.BluetoothScanningMode.ACTIVE,
        )
    )

    return True
