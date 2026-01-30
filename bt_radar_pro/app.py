import logging
import asyncio
import threading
import os
import json
from flask import Flask, render_template_string, request, redirect
from bleak import BleakScanner

# Configurazione LOG Professionale
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("RadarPro")

app = Flask(__name__)
CONFIG_FILE = "/data/radar_settings.json"
discovered_devices = {}

logger.info("🛠️ Inizializzazione Motore Radar Pro...")

def scan_callback(device, advertisement_data):
    mac = device.address
    rssi = advertisement_data.rssi
    name = advertisement_data.local_name or device.name or "Sconosciuto"
    
    # Path Loss Model per distanza
    tx_power = -59
    distance = round(10**((tx_power - rssi) / (20)), 2)
    
    discovered_devices[mac] = {
        "name": name,
        "rssi": rssi,
        "dist": distance
    }

async def start_ble_scanner():
    try:
        logger.info("📡 Tentativo di accesso all'antenna Bluetooth...")
        scanner = BleakScanner(scan_callback)
        await scanner.start()
        logger.info("✅ Motore Bluetooth avviato correttamente!")
        while True:
            await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"❌ ERRORE CRITICO BLUETOOTH: {str(e)}")
        logger.error("👉 Suggerimento: Assicurati che l'add-on abbia i permessi 'bluetooth' e 'dbus' nel config.yaml")

def run_ble_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(start_ble_scanner())
    except Exception as e:
        logger.error(f"🧵 Errore nel thread Bluetooth: {e}")

# Avvio del thread Bluetooth
threading.Thread(target=run_ble_thread, daemon=True).start()

@app.route('/')
def index():
    # Se la lista è vuota, mostriamo un messaggio di diagnostica
    if not discovered_devices:
        status_msg = "<p style='color: #ffa500;'>⏳ Scansione in corso o antenna non rilevata. Controlla i Log del Supervisor.</p>"
    else:
        status_msg = ""

    # (Logica della pagina web identica alla precedente...)
    # ... (omessa per brevità ma inclusa nel tuo commit) ...
    return f"<html><body><h1>Radar Pro</h1>{status_msg}</body></html>" # Esempio semplificato

if __name__ == '__main__':
    logger.info("🌐 Avvio Interfaccia Web su porta 8099")
    app.run(host='0.0.0.0', port=8099)
