from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN

class BluetoothRadarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Step 1: Selezione del dispositivo tracciato."""
        # Recuperiamo i dati dal coordinator (se già avviato)
        # Per ora facciamo una configurazione semplice per attivare l'integrazione
        if user_input is not None:
            return self.async_create_entry(title="Radar Pro Attivo", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("device_name", default="Mio Telefono"): str,
            })
        )
