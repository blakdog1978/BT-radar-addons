import logging
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.components import bluetooth

_LOGGER = logging.getLogger(__name__)

class BluetoothRadarCoordinator(DataUpdateCoordinator):
    """Gestisce la scoperta e il filtraggio dei dispositivi."""

    def __init__(self, hass):
        super().__init__(hass, _LOGGER, name="BT Radar Coordinator")
        self.devices = {} # Storage dei segnali: {mac: {data}}

    def update_device(self, mac, rssi, scanner):
        """Aggiorna i dati e calcola il movimento."""
        if mac not in self.devices:
            self.devices[mac] = {
                "rssi_history": [],
                "name": mac,
                "scanner": scanner,
                "is_moving": False,
                "distance": 0
            }
        
        hist = self.devices[mac]["rssi_history"]
        hist.append(rssi)
        if len(hist) > 10: hist.pop(0)

        # Calcolo Movimento (Varianza RSSI)
        if len(hist) > 5:
            diff = max(hist) - min(hist)
            self.devices[mac]["is_moving"] = diff > 6 # 6dB di scarto = movimento
        
        self.devices[mac]["distance"] = round(10**((-60 - rssi) / 22), 2)
        self.devices[mac]["scanner"] = scanner
