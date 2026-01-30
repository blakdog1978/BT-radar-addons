import asyncio
import json
import os
import threading
import logging
import websockets
from flask import Flask, jsonify

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("RadarBypass")

app = Flask(__name__)
SUPERVISOR_TOKEN = os.getenv('SUPERVISOR_TOKEN')
radar_data = {}

async def event_bus_listener():
    uri = "ws://supervisor/core/api/websocket"
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                # 1. Autenticazione (Handshake obbligatorio)
                await websocket.recv()
                await websocket.send(json.dumps({"type": "auth", "access_token": SUPERVISOR_TOKEN}))
                auth = json.loads(await websocket.recv())
                if auth.get("type") != "auth_ok":
                    logger.error("❌ Token non valido"); return

                # 2. SOTTOSCRIZIONE GLOBALE (Lo "Scavallamento")
                # Ascoltiamo tutti i cambiamenti di stato
                await websocket.send(json.dumps({
                    "id": 1,
                    "type": "subscribe_events",
                    "event_type": "state_changed"
                }))
                
                logger.info("📡 Intercettatore Eventi Globale Attivo. Filtro Bluetooth in corso...")
                
                async for message in websocket:
                    data = json.loads(message)
                    if data.get("type") == "event":
                        event_data = data.get("event", {}).get("data", {})
                        new_state = event_data.get("new_state", {})
                        attrs = new_state.get("attributes", {})
                        
                        # FILTRO: Se l'evento ha RSSI o sorgente Bluetooth, lo prendiamo
                        if "rssi" in attrs or attrs.get("source_type") == "bluetooth_le":
                            eid = event_data.get("entity_id")
                            rssi = attrs.get("rssi")
                            dist = attrs.get("distance", 0)
                            
                            # Se non c'è la distanza, la calcoliamo noi
                            if not dist and rssi:
                                dist = round(10**((-60 - rssi) / 22), 2)
                            
                            radar_data[eid] = {
                                "name": attrs.get("friendly_name", eid),
                                "distance": dist,
                                "proxy": attrs.get("scanner") or attrs.get("source") or "Sorgente HA",
                                "rssi": rssi
                            }
        except Exception as e:
            logger.error(f"🔄 Connessione persa: {e}")
            await asyncio.sleep(5)

threading.Thread(target=lambda: asyncio.run(event_bus_listener()), daemon=True).start()

@app.route('/api/data')
def get_data():
    return jsonify(radar_data)

@app.route('/')
def index():
    return """
    <html>
        <head>
            <style>
                body { background:#0d1117; color:white; font-family:sans-serif; padding:15px; }
                .card { background:#161b22; border:1px solid #333; padding:10px; margin:10px 0; border-radius:8px; }
                .val { color:#58a6ff; font-weight:bold; }
            </style>
        </head>
        <body>
            <h2 style="text-align:center;">🛰️ Radar Bypass v1.17</h2>
            <div id="status" style="text-align:center; color:#8b949e; font-size:0.8em;">In ascolto sul bus eventi...</div>
            <div id="list"></div>
            <script>
                async function update() {
                    const r = await fetch('/api/data');
                    const data = await r.json();
                    let html = "";
                    for(let id in data) {
                        html += `<div class="card">
                            <b>${data[id].name}</b><br>
                            Distanza: <span class="val">${data[id].distance}m</span> | RSSI: ${data[id].rssi}<br>
                            <small>Sorgente: ${data[id].proxy}</small>
                        </div>`;
                    }
                    document.getElementById('list').innerHTML = html || "<p style='text-align:center;'>Nessun evento Bluetooth rilevato sul bus.</p>";
                    document.getElementById('status').innerText = "Ultimo check: " + new Date().toLocaleTimeString();
                }
                setInterval(update, 2000);
            </script>
        </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8099)