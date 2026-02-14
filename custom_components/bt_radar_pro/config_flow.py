from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN, EVENT_CALIBRATION_START, EVENT_CALIBRATION_STOP
from homeassistant.components import bluetooth
from homeassistant.helpers import selector
import logging

_LOGGER = logging.getLogger(__name__)

class BluetoothRadarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Step 1: Selezione del dispositivo tracciato."""
        errors = {}
        
        # Scansiona i dispositivi Bluetooth disponibili e crea una lista
        scanned_devices = bluetooth.async_scanner_devices(self.hass)
        device_options = {}

        for device in scanned_devices:
            # Mostra Nome (o MAC) per la selezione
            name = device.name if device.name else device.address
            device_options[device.address] = f"{name} ({device.address})"

        if user_input is not None:
            # Validazione: Selezionato un dispositivo valido
            if user_input["mac_address"] in device_options:
                self.selected_mac = user_input["mac_address"]
                # Usa nome personalizzato se fornito, altrimenti nome BT
                self.selected_name = user_input.get("custom_name") or device_options[self.selected_mac].split(" (")[0]
                return await self.async_step_area()
            else:
                errors["base"] = "device_not_found"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("mac_address"): vol.In(device_options),
                vol.Optional("custom_name"): str,
            }),
            errors=errors
        )

    async def async_step_area(self, user_input=None):
        """Step 2: Selezione Area/Stanza."""
        errors = {}

        if user_input is not None:
            # Crea l'entry di configurazione finale
            return self.async_create_entry(
                title=f"Radar: {self.selected_name}",
                data={
                    "mac_address": self.selected_mac,
                    "name": self.selected_name,
                    "area_id": user_input["area_id"]
                }
            )

        return self.async_show_form(
            step_id="area",
            data_schema=vol.Schema({
                vol.Required("area_id"): selector.AreaSelector(
                    selector.AreaSelectorConfig(multiple=False)
                )
            }),
            errors=errors
        )

    # --- CALIBRATION OPTIONS FLOW ---
    @staticmethod
    def async_get_options_flow(config_entry):
        return BluetoothRadarOptionsFlow(config_entry)

class BluetoothRadarOptionsFlow(config_entries.OptionsFlow):
    """Gestisce la calibrazione post-installazione."""

    def __init__(self, config_entry):
        self.config_entry = config_entry
        self.coordinator = None # Sarà popolato nello step init

    async def async_step_init(self, user_input=None):
        """Menu opzioni: Calibrazione o Modifica."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["calibrate_perimeter", "calibrate_center", "manage_settings"]
        )

    async def async_step_calibrate_perimeter(self, user_input=None):
        """Step: Calibrazione Perimetro (Start/Stop)."""
        coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]
        
        if user_input is not None:
            # Avvia la registrazione del perimetro
            coordinator.start_calibration("perimeter")
            return await self.async_step_calibrate_recording()

        return self.async_show_form(
            step_id="calibrate_perimeter",
            description_placeholders={"device_name": self.config_entry.data["name"]},
            data_schema=vol.Schema({}) # Solo un bottone "Start"
        )

    async def async_step_calibrate_center(self, user_input=None):
        """Step: Calibrazione Centro (Start/Stop)."""
        coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]

        if user_input is not None:
            # Avvia la registrazione del centro
            coordinator.start_calibration("center")
            return await self.async_step_calibrate_recording()

        return self.async_show_form(
            step_id="calibrate_center",
            description_placeholders={"device_name": self.config_entry.data["name"]},
            data_schema=vol.Schema({})
        )

    async def async_step_calibrate_recording(self, user_input=None):
        """Schermata di attesa mentre registri i dati."""
        coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]

        if user_input is not None:
            # Stop registrazione e salva
            coordinator.stop_calibration()
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="calibrate_recording",
            description_placeholders={"status": "Recording... Walk around!"},
            data_schema=vol.Schema({
                vol.Required("confirm_stop", default=True): bool
            })
        )
