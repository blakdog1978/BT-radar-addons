# BT Radar Pro - Architectural Plan

## Goal
Create a Home Assistant integration ("BT Radar Pro") to locate Bluetooth devices within the home using signal triangulation from multiple ESPHome/Bluetooth proxies.

## Key Features
1.  **Guided Setup (Config Flow):**
    *   Select device to track (scan available BT devices).
    *   Rename device.
    *   Select Room (Area).
2.  **Calibration Wizard:**
    *   **Step 1: Perimeter:** Walk the room boundary to learn signal characteristics.
    *   **Step 2: Center:** Stand in the center to establish a baseline.
    *   **Step 3: Triangulation:** Use RSSI data from multiple proxies to build a signal map.
3.  **Tracking Logic:**
    *   Compare real-time RSSI against calibrated maps.
    *   Determine room occupancy based on highest probability/signal match.
    *   Expose a `device_tracker` entity.

## Component Structure
*   `manifest.json`: Metadata.
*   `config_flow.py`: The wizard logic (Device selection -> Room selection -> Calibration steps).
*   `coordinator.py`: The brain. Handles BT scanning, data aggregation, and position calculation.
*   `sensor.py` / `device_tracker.py`: Entities to expose the location.
*   `translations/`: For multi-language support (Italian/English).

## Implementation Steps
1.  **Refine Config Flow:**
    *   Add scanning step to list BT devices.
    *   Add area selection step.
    *   Add calibration steps (start/stop recording RSSI).
2.  **Enhance Coordinator:**
    *   Implement multi-proxy data collection.
    *   Implement calibration storage (save RSSI fingerprints per room).
    *   Implement triangulation/fingerprinting algorithm.
3.  **Create Entities:**
    *   `device_tracker.bt_radar_DEVICE_NAME`: Shows current room.
    *   `sensor.bt_radar_DEVICE_NAME_distance`: Optional distance metrics.

## Next Action
I will start by implementing the `config_flow.py` to handle device selection and room assignment, then move to the calibration logic.
