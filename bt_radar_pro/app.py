import asyncio
import json
import os
import threading
import logging
import websockets
from flask import Flask, render_template_string, request, redirect

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("RadarWS")

app = Flask(__name__)
CONFIG_FILE = "/data/radar_settings.json"
SUPERVISOR_TOKEN = os.getenv('SUPERVISOR_TOKEN')

discovered_devices = {}
total_packets = 0 

async def listen_to_ha_bluetooth():
    global total_packets
    uri = "ws://supervisor/core/api/websocket"
    
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                await websocket.send(json.dumps({"type": "auth", "access_token": SUPERVISOR_TOKEN}))
                await websocket.send(json.dumps({"id": 1, "type": "bluetooth/subscribe"}))
                
                logger.info("✅ WebSocket Connesso. In attesa di dati reali...")
                
                async for message in websocket:
                    total_packets += 1
                    data = json.loads(message)
                    
                    # LOG DI DEBUG - Vediamo cosa arriva davvero
                    if data.get("type") == "event":
                        event = data.get("event", {})
                        mac = event.get("address")
                        rssi = event.get("rssi")
                        
                        if mac:
                            logger.info(f"📡 RILEVATO: {mac} | RSSI: {rssi}")
                            dist = round(10**((-60 - rssi) / 20), 2)
                            discovered_devices[mac] = {
                                "rssi": rssi,
                                "dist": dist,
                                "proxy": event.get("source", "Unknown")
                            }
        except Exception as e:
            logger.error(f"❌ Errore: {e}")
            await asyncio.sleep(5)

threading.Thread(target=lambda: asyncio.run(listen_to_ha_bluetooth()), daemon=True).start()

# ... (Resto del codice Flask identico alla 1.6.1) ...
@app.route('/')
def index():
    # Carica settings e genera HTML (usa il codice della 1.6.1)
    return f"<html><body><h1>Pacchetti: {total_packets}</h1><pre>{json.dumps(discovered_devices, indent=2)}</pre></body></html>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8099)