"""Coordinator for Bluetooth Radar Pro."""
from __future__ import annotations

import logging
from datetime import timedelta
import statistics
import json

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.components import bluetooth
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_MAC, CONF_NAME, CONF_AREA

_LOGGER = logging.getLogger(__name__)

class BluetoothRadarCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Bluetooth data and triangulation."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        self.entry = entry
        self.mac_address = entry.data[CONF_MAC]
        self.device_name = entry.data[CONF_NAME]
        self.hass = hass
        
        # Calibration State
        self._calibration_mode = None  # None, "perimeter", "center"
        self._calibration_data_buffer = {}  # {proxy_id: [rssi1, rssi2...]}

        # Runtime Data
        self.data = {
            "best_source": None,
            "best_rssi": -100,
            "proxies": {},       # {proxy_id: current_rssi}
            "is_home": False,
            "current_room": None, # The calculated room based on triangulation
            "confidence": 0.0     # 0.0 to 1.0
        }

        super().__init__(
            hass,
            _LOGGER,
            name=f"Bluetooth Radar {self.device_name}",
            update_interval=timedelta(seconds=2), # Fast update for real-time tracking
        )

        self._unsubscribe_callback = None

    async def async_config_entry_first_refresh(self):
        """Start listening to bluetooth callbacks."""
        self._unsubscribe_callback = bluetooth.async_register_callback(
            self.hass,
            self._async_handle_bluetooth_event,
            {"address": self.mac_address, "connectable": False},
            bluetooth.BluetoothScanningMode.ACTIVE
        )
        
        # Initial scan
        service_info = bluetooth.async_last_service_info(self.hass, self.mac_address, connectable=False)
        if service_info:
            self._update_data(service_info)

    @callback
    def _async_handle_bluetooth_event(self, service_info, change):
        """Handle a Bluetooth event."""
        self._update_data(service_info)

    def _update_data(self, service_info: bluetooth.BluetoothServiceInfoBleak):
        """Update data from service info and calculate position."""
        rssi = service_info.rssi
        source = service_info.source
        
        # 1. Update Raw Data
        self.data["proxies"][source] = rssi
        self.data["is_home"] = True

        # 2. Calibration Mode: Accumulate Data
        if self._calibration_mode:
            if source not in self._calibration_data_buffer:
                self._calibration_data_buffer[source] = []
            self._calibration_data_buffer[source].append(rssi)
            # Log for debug
            # _LOGGER.debug(f"Calibration ({self._calibration_mode}): {source}={rssi}")

        # 3. Triangulation (Normal Mode)
        else:
            self._calculate_position()

        # 4. Notify Listeners
        self.async_set_updated_data(self.data)

    def start_calibration(self, mode: str):
        """Start calibration process (perimeter or center)."""
        _LOGGER.info(f"Starting calibration: {mode} for {self.device_name}")
        self._calibration_mode = mode
        self._calibration_data_buffer = {} # Clear buffer

    def stop_calibration(self):
        """Stop calibration and save fingerprint."""
        if not self._calibration_mode:
            return

        _LOGGER.info(f"Stopping calibration: {self._calibration_mode}")
        
        # Calculate Average RSSI per proxy
        fingerprint = {}
        for proxy, rssi_list in self._calibration_data_buffer.items():
            if rssi_list:
                avg_rssi = statistics.mean(rssi_list)
                fingerprint[proxy] = round(avg_rssi, 1)

        # Save to Config Entry Options
        # Structure: options = { "calibration": { "perimeter": {...}, "center": {...} } }
        new_options = dict(self.entry.options)
        if "calibration" not in new_options:
            new_options["calibration"] = {}
        
        # Save specific mode data
        new_options["calibration"][self._calibration_mode] = fingerprint
        
        self.hass.config_entries.async_update_entry(self.entry, options=new_options)
        
        _LOGGER.info(f"Saved calibration data: {fingerprint}")
        
        # Reset state
        self._calibration_mode = None
        self._calibration_data_buffer = {}

    def _calculate_position(self):
        """Determine room based on stored calibration fingerprints."""
        
        # Get calibration data from options
        calibration = self.entry.options.get("calibration", {})
        if not calibration:
            # Fallback: Best RSSI (Simpler logic if no calibration)
            best_rssi = -100
            best_source = None
            for src, val in self.data["proxies"].items():
                if val > best_rssi:
                    best_rssi = val
                    best_source = src
            self.data["best_rssi"] = best_rssi
            self.data["best_source"] = best_source
            self.data["current_room"] = best_source # Temporary fallback
            return

        # Fingerprint Matching Logic (Euclidean Distance / Nearest Neighbor)
        # We compare current_proxies_rssi vector vs stored_calibration_vectors
        
        current_fingerprint = self.data["proxies"]
        best_match_score = float('inf') # Lower is better (distance)
        best_match_room = None

        # Check Center Fingerprint
        center_fp = calibration.get("center", {})
        if center_fp:
            score = self._calculate_fingerprint_distance(current_fingerprint, center_fp)
            if score < best_match_score:
                best_match_score = score
                best_match_room = "Center/Inside"

        # Check Perimeter Fingerprint (Could treat as 'Edge')
        perim_fp = calibration.get("perimeter", {})
        if perim_fp:
            score = self._calculate_fingerprint_distance(current_fingerprint, perim_fp)
            if score < best_match_score:
                best_match_score = score
                best_match_room = "Perimeter/Edge"
        
        # Confidence calculation (inverse of distance)
        confidence = 100 - min(best_match_score, 100)
        
        self.data["current_room"] = best_match_room
        self.data["confidence"] = round(confidence, 1)
        
        # Find best single source for display
        best_rssi = -100
        best_source = None
        for src, val in self.data["proxies"].items():
            if val > best_rssi:
                best_rssi = val
                best_source = src
        self.data["best_rssi"] = best_rssi
        self.data["best_source"] = best_source

    def _calculate_fingerprint_distance(self, current: dict, stored: dict) -> float:
        """Calculate Euclidean distance between two RSSI vectors."""
        # Keys (proxies) might not match perfectly.
        # If a proxy is missing in one but present in other, assume weak signal (-100 dBm)
        
        all_proxies = set(current.keys()) | set(stored.keys())
        sum_sq_diff = 0
        
        for proxy in all_proxies:
            val_curr = current.get(proxy, -100) # Default weak if missing
            val_stored = stored.get(proxy, -100)
            
            diff = val_curr - val_stored
            sum_sq_diff += diff * diff
            
        return (sum_sq_diff ** 0.5) # Sqrt(Sum(Diff^2))

    async def async_unload(self):
        """Stop listening."""
        if self._unsubscribe_callback:
            self._unsubscribe_callback()
