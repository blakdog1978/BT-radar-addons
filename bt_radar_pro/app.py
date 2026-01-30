import asyncio
import json
import os
import threading
import logging
import websockets
from flask import Flask, render_template_string, request, redirect

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("RadarDebug")

app = Flask(__name__)
CONFIG_FILE = "/data/radar_settings.json"
SUPERVISOR_TOKEN = os.getenv('SUPERVISOR_TOKEN')

# Stato globale
discovered_devices = {}
total_events = 0
ws_status = "Inizializzazione..."

async def monitor_bluetooth():
    global total_events, ws_status
    uri = "ws://supervisor/core/api/websocket"
    
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                # 1. Autenticazione
                await websocket.send(json.dumps({"type": "auth", "access_token": SUPERVISOR_TOKEN}))
                auth_resp = json.loads(await websocket.recv())
                if auth_resp.get("type") != "auth_ok":
                    ws_status = "❌ Errore Autenticazione"
                    logger.error(ws_status)
                    return

                # 2. Richiesta Sottoscrizione
                await websocket.send(json.dumps({
                    "id": 10,
                    "type": "bluetooth/subscribe"
                }))
                
                # 3. Controllo se HA accetta la sottoscrizione
                sub_resp = json.loads(await websocket.recv())
                if sub_resp.get("success"):
                    ws_status = "✅ Flusso Bluetooth ATTIVO"
                    logger.info(ws_status)
                else:
                    ws_status = f"⚠️ Sottoscrizione negata: {sub_resp.get('error', {}).get('message', 'Errore sconosciuto')}"
                    logger.warning(ws_status)

                # 4. Ascolto pacchetti
                async for message in websocket:
                    data = json.loads(message)
                    if data.get("type") == "event":
                        total_events += 1
                        event = data.get("event", {})
                        mac = event.get("address")
                        if mac:
                            rssi = event.get("rssi")
                            dist = round(10**((-60 - rssi) / 22), 2)
                            discovered_devices[mac] = {
                                "rssi": rssi,
                                "dist": dist,
                                "proxy": event.get("source", "Proxy").replace("_", " ").title()
                            }
        except Exception as e:
            ws_status = f"❌ Connessione persa: {e}"
            logger.error(ws_status)
            await asyncio.sleep(5)

threading.Thread(target=lambda: asyncio.run(monitor_bluetooth()), daemon=True).start()

@app.route('/')
def index():
    device_rows = "".join([f"<tr><td>{m}</td><td><b>{d['dist']}m</b></td><td>{d['proxy']}</td></tr>" for m, d in discovered_devices.items()])
    return f"""
    <html>
        <head><meta http-equiv="refresh" content="2">
        <style>
            body {{ background:#0d1117; color:white; font-family:sans-serif; padding:20px; }}
            .status {{ padding:10px; border-radius:8px; background:#161b22; border:1px solid #333; margin-bottom:20px; }}
            table {{ width:100%; border-collapse:collapse; }}
            td, th {{ padding:10px; border-bottom:1px solid #333; text-align:left; }}
        </style></head>
        <body>
            <h1>🛰️ Radar Deep Debug</h1>
            <div class="status">
                Stato WS: <b>{ws_status}</b><br>
                Eventi ricevuti: <b style="color:#2ea043;">{total_events}</b>
            </div>
            { "<table><tr><th>MAC</th><th>Distanza</th><th>Sorgente</th></tr>" + device_rows + "</table>" if discovered_devices else "<p>In attesa di dati... se il contatore eventi è fermo, il problema è nei permessi di HA.</p>" }
        </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8099)